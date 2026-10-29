
from fastapi.testclient import TestClient

import backend.app.main as main
from backend.app.main import app, runs

client = TestClient(app)

VALID_PROPOSAL = {
    "building_use": "residential",
    "plot_area": 1200,
    "road_width": 9,
    "proposed_height": 12,
    "zone": "residential",
}


def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Building Plan Compliance API is running"
    }


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_check_valid_proposal():
    response = client.post("/check", json=VALID_PROPOSAL)

    assert response.status_code == 200

    data = response.json()
    assert data["building_details"] == VALID_PROPOSAL
    assert data["findings"] == []
    assert data["status"] == "pending_rules_check"


def test_check_rejects_missing_required_field():
    proposal = VALID_PROPOSAL.copy()
    proposal.pop("plot_area")

    response = client.post("/check", json=proposal)

    assert response.status_code == 422


def test_check_rejects_non_numeric_plot_area():
    proposal = VALID_PROPOSAL.copy()
    proposal["plot_area"] = "not-a-number"

    response = client.post("/check", json=proposal)

    assert response.status_code == 422


def test_cors_preflight_for_frontend():
    response = client.options(
        "/check",
        headers={
            "Origin": "http://127.0.0.1:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://127.0.0.1:5500"
    )


def test_start_run_and_retrieve_result(monkeypatch):
    def workflow_without_evidence(state):
        return {
            **state,
            "status": "needs_review",
            "findings": [
                "Insufficient regulatory evidence; manual review required."
            ],
            "clauses": [],
            "citations": [],
        }

    monkeypatch.setattr(
        main.compliance_workflow,
        "invoke",
        workflow_without_evidence,
    )

    response = client.post("/runs", json=VALID_PROPOSAL)

    assert response.status_code == 202

    data = response.json()
    run_id = data["run_id"]

    assert data["status"] == "pending"
    assert run_id in runs

    # TestClient executes background tasks before the request completes.
    result = client.get(f"/runs/{run_id}")

    assert result.status_code == 200

    result_data = result.json()
    assert result_data["run_id"] == run_id
    assert result_data["status"] == "completed"
    assert result_data["workflow_status"] == "needs_review"

    assert any(
        "evidence" in finding.lower()
        or "retrieval" in finding.lower()
        for finding in result_data["findings"]
    )

    assert result_data["clauses"] == []
    assert result_data["citations"] == []


def test_unknown_run_returns_404():
    response = client.get("/runs/unknown-run-id")

    assert response.status_code == 404


def test_failed_run_does_not_expose_internal_error(monkeypatch):
    def failing_workflow(state):
        raise RuntimeError("Sensitive internal details")

    monkeypatch.setattr(
        main.compliance_workflow,
        "invoke",
        failing_workflow,
    )

    response = client.post("/runs", json=VALID_PROPOSAL)

    assert response.status_code == 202

    run_id = response.json()["run_id"]
    result = client.get(f"/runs/{run_id}")

    assert result.status_code == 200

    result_data = result.json()

    assert result_data["run_id"] == run_id
    assert result_data["status"] == "failed"

    # Failed runs may omit workflow_status; internal errors must stay private.
    assert "Sensitive internal details" not in result.text
