
from uuid import uuid4

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(
    title="Building Plan Compliance Pre-Check",
    version="0.1.0",
)

# Development-only origins for the local frontend.
# The frontend will be served from http://127.0.0.1:5500.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

runs = {}


class BuildingProposal(BaseModel):
    building_use: str
    plot_area: float
    road_width: float
    proposed_height: float
    zone: str


def validate_proposal(proposal: dict):
    findings = []

    for field in [
        "building_use",
        "plot_area",
        "road_width",
        "proposed_height",
        "zone",
    ]:
        if field not in proposal:
            findings.append(f"Missing required field: {field}")

    for field in ["plot_area", "road_width", "proposed_height"]:
        if field in proposal and proposal[field] <= 0:
            findings.append(f"{field} must be greater than zero.")

    return findings


def process_run(run_id: str, proposal: dict):
    findings = validate_proposal(proposal)
    runs[run_id]["findings"] = findings
    runs[run_id]["status"] = (
        "needs_review" if findings else "completed"
    )


@app.get("/")
def home():
    return {"message": "Building Plan Compliance API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/check")
def check_proposal(proposal: BuildingProposal):
    details = proposal.model_dump()
    findings = validate_proposal(details)

    return {
        "building_details": details,
        "findings": findings,
        "status": "needs_review" if findings else "pending_rules_check",
    }


@app.post("/runs", status_code=202)
def start_run(
    proposal: BuildingProposal,
    background_tasks: BackgroundTasks,
):
    run_id = str(uuid4())

    runs[run_id] = {
        "run_id": run_id,
        "status": "pending",
        "findings": [],
    }

    background_tasks.add_task(
        process_run,
        run_id,
        proposal.model_dump(),
    )

    return runs[run_id]


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")

    return runs[run_id]
