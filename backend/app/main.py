from __future__ import annotations

import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.middleware.cors import CORSMiddleware

from backend.app import storage
from backend.app.jobs import enqueue_run, run_sync
from backend.app.metrics import metrics
from backend.app.rate_limiter import SlidingWindowRateLimiter
from backend.app.run_service import execute_run


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("building_plan_compliance")
run_limiter = SlidingWindowRateLimiter(
    limit=int(os.getenv("RUNS_PER_MINUTE", "30")),
    window_seconds=60,
)
@asynccontextmanager
async def lifespan(_: FastAPI):
    storage.initialize()
    yield


app = FastAPI(
    title="Building Plan Compliance Pre-Check",
    version="1.0.0",
    lifespan=lifespan,
    description=(
        "Evidence retrieval and review routing only. This service does not "
        "certify legal or regulatory compliance."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)


class BuildingProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    building_use: Literal["residential", "commercial", "mixed-use", "institutional"]
    plot_area: float = Field(gt=0, le=2_000_000, allow_inf_nan=False)
    road_width: float = Field(gt=0, le=200, allow_inf_nan=False)
    proposed_height: float = Field(gt=0, le=300, allow_inf_nan=False)
    zone: str = Field(min_length=1, max_length=100)
    site_width: float | None = Field(default=None, gt=0, le=1000, allow_inf_nan=False)
    site_depth: float | None = Field(default=None, gt=0, le=1000, allow_inf_nan=False)
    proposed_coverage_percent: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    proposed_far: float | None = Field(default=None, ge=0, le=50, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_site_dimensions(self):
        if self.site_width is not None and self.site_depth is not None:
            if self.plot_area > self.site_width * self.site_depth:
                raise ValueError("plot_area cannot exceed site_width multiplied by site_depth")
        return self


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    satisfactory: bool
    reason: str = Field(min_length=3, max_length=1000)


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied = request.headers.get("X-Correlation-ID", "")
    correlation_id = supplied if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", supplied) else str(uuid4())
    request.state.correlation_id = correlation_id
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - started
    metrics.observe("http_request_duration_seconds", elapsed)
    metrics.increment("http_requests_total", labels={"method": request.method, "path": getattr(request.scope.get("route"), "path", request.url.path), "status": str(response.status_code)})
    response.headers["X-Correlation-ID"] = correlation_id
    logger.info(json.dumps({
        "event": "http_request",
        "correlation_id": correlation_id,
        "method": request.method,
        "path": getattr(request.scope.get("route"), "path", request.url.path),
        "status_code": response.status_code,
        "duration_seconds": round(elapsed, 6),
    }, separators=(",", ":")))
    return response


@app.exception_handler(RequestValidationError)
async def quarantine_invalid_request(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(part) for part in error.get("loc", []) if part != "body"),
            "type": error.get("type", "validation_error"),
            "message": error.get("msg", "Invalid value"),
        })
    quarantine_id = storage.quarantine_rejection(await request.body(), errors)
    logger.warning(json.dumps({
        "event": "request_quarantined",
        "correlation_id": getattr(request.state, "correlation_id", None),
        "quarantine_id": quarantine_id,
        "field_errors": errors,
    }, separators=(",", ":")))
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request failed the published proposal data contract.",
            "quarantine_id": quarantine_id,
            "field_errors": errors,
            "agent_started": False,
            "recommendation": "revise-and-recheck",
        },
    )


@app.get("/")
def home():
    return {"message": "Building Plan Compliance API is running"}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "api"}


@app.get("/health/ready")
def readiness():
    try:
        import chromadb
        from agents.rag.vector_store import COLLECTION_NAME
        client = chromadb.PersistentClient(path=os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db"))
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
    except Exception:
        count = 0
    if count < 1:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "indexed_chunks": count})
    return {"status": "ready", "indexed_chunks": count}


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return metrics.render()


@app.post("/check")
def check_proposal(proposal: BuildingProposal):
    return {
        "building_details": proposal.model_dump(),
        "findings": [],
        "recommendation": "specialist-review",
        "status": "validated",
        "note": "Input validation only; submit to /runs for evidence retrieval.",
    }


@app.post("/runs", status_code=202)
def start_run(proposal: BuildingProposal, request: Request):
    client_key = request.client.host if request.client else "unknown"
    allowed, retry_after = run_limiter.consume(client_key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Run submission rate limit exceeded.",
            headers={"Retry-After": str(retry_after)},
        )
    run_id = str(uuid4())
    correlation_id = request.state.correlation_id
    details = proposal.model_dump()
    storage.create_run(run_id, details, correlation_id)
    metrics.increment("compliance_runs_submitted_total")
    queue_mode = enqueue_run(run_id, details, correlation_id)
    if queue_mode == "local":
        run_sync(run_id, details, correlation_id)
    return {
        "run_id": run_id,
        "status": "pending",
        "recommendation": None,
        "correlation_id": correlation_id,
        "queue_mode": queue_mode,
        "poll_url": f"/runs/{run_id}",
    }


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    record = storage.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return record


@app.get("/quarantine/{quarantine_id}")
def get_quarantined_request(quarantine_id: str):
    record = storage.get_quarantine(quarantine_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Quarantine record not found")
    return record


@app.post("/runs/{run_id}/feedback", status_code=201)
def submit_feedback(run_id: str, feedback: FeedbackRequest):
    try:
        record = storage.save_feedback(run_id, feedback.satisfactory, feedback.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    metrics.increment("feedback_submissions_total", labels={"satisfactory": str(feedback.satisfactory).lower()})
    return record


@app.get("/feedback/summary")
def get_feedback_summary():
    return storage.feedback_summary()



