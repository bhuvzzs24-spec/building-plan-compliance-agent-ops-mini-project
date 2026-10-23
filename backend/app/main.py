
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure the repository root is importable when the API starts.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.workflow import compliance_workflow


app = FastAPI(
    title="Building Plan Compliance Pre-Check",
    version="0.2.0",
)

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
    plot_area: float = Field(gt=0)
    road_width: float = Field(gt=0)
    proposed_height: float = Field(gt=0)
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
        elif isinstance(proposal[field], str) and not proposal[field].strip():
            findings.append(f"{field} must not be empty.")

    for field in ("plot_area", "road_width", "proposed_height"):
        value = proposal.get(field)
        if value is not None and value <= 0:
            findings.append(f"{field} must be greater than zero.")

    return findings


def process_run(run_id: str, proposal: dict):
    """Validate the proposal and run Sloka's compliance retrieval workflow."""
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

        initial_state = {
            "building_details": proposal,
            "findings": [],
            "status": "",
            "clauses": [],
            "citations": [],
        }

        result = compliance_workflow.invoke(initial_state)

        workflow_findings = result.get("findings", [])
        clauses = result.get("clauses", [])
        citations = result.get("citations", [])

        runs[run_id].update({
            "status": "completed",
            "workflow_status": result.get("status", "unknown"),
            "findings": workflow_findings,
            "clauses": clauses,
            "citations": citations,
            "building_details": proposal,
        })

    except Exception as exc:
        runs[run_id].update({
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "findings": [],
            "clauses": [],
            "citations": [],
        })


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
        raise HTTPException(status_code=404, detail="Run not found")

    return runs[run_id]
