
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.workflow import compliance_workflow


WORKFLOW_TIMEOUT_SECONDS = 30

app = FastAPI(
    title="Building Plan Compliance Pre-Check",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://building-plan-compliance-frontend.onrender.com",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

runs = {}


class BuildingProposal(BaseModel):
    building_use: str
    plot_area: float = Field(gt=0, allow_inf_nan=False)
    road_width: float = Field(gt=0, allow_inf_nan=False)
    proposed_height: float = Field(gt=0, allow_inf_nan=False)
    zone: str


def validate_proposal(proposal: dict):
    findings = []

    for field in (
        "building_use",
        "plot_area",
        "road_width",
        "proposed_height",
        "zone",
    ):
        if field not in proposal or proposal[field] is None:
            findings.append(f"Missing required field: {field}")
        elif (
            isinstance(proposal[field], str)
            and not proposal[field].strip()
        ):
            findings.append(f"{field} must not be empty.")

    for field in ("plot_area", "road_width", "proposed_height"):
        value = proposal.get(field)
        if value is not None and value <= 0:
            findings.append(f"{field} must be greater than zero.")

    return findings


async def process_run(run_id: str, proposal: dict):
    """Run the workflow with bounded waiting and safe error responses."""
    try:
        findings = validate_proposal(proposal)

        if findings:
            runs[run_id].update({
                "status": "needs_review",
                "findings": findings,
                "clauses": [],
                "citations": [],
            })
            return

        runs[run_id]["status"] = "running"

        initial_state = {
            "building_details": proposal,
            "findings": [],
            "status": "",
            "clauses": [],
            "citations": [],
        }

        result = await asyncio.wait_for(
            asyncio.to_thread(
                compliance_workflow.invoke,
                initial_state,
            ),
            timeout=WORKFLOW_TIMEOUT_SECONDS,
        )

        runs[run_id].update({
            "status": "completed",
            "workflow_status": result.get("status", "unknown"),
            "findings": result.get("findings", []),
            "clauses": result.get("clauses", []),
            "citations": result.get("citations", []),
            "building_details": proposal,
        })

    except asyncio.TimeoutError:
        runs[run_id].update({
            "status": "failed",
            "error": "The compliance workflow timed out. Please try again.",
            "findings": [],
            "clauses": [],
            "citations": [],
        })

    except Exception:
        runs[run_id].update({
            "status": "failed",
            "error": "The compliance workflow failed.",
            "findings": [],
            "clauses": [],
            "citations": [],
        })


@app.get("/")
def home():
    return {
        "message": "Building Plan Compliance API is running"
    }


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
        "status": (
            "needs_review" if findings else "pending_rules_check"
        ),
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
        "clauses": [],
        "citations": [],
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
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    return runs[run_id]
