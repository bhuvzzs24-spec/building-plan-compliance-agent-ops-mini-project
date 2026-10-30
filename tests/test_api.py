import time

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

VALID_PROPOSAL = {
    "building_use": "residential",
    "plot_area": 200,
    "road_width": 6,
    "proposed_height": 9,
    "zone": "A - intensely developed area",
    "site_width": 10,
    "site_depth": 20,
}


class FakeWorkflow:
    def invoke(self, state):
        return {
            **state,
            "status": "completed",
            "recommendation": "specialist-review",
            "findings": [{"provision": "setbacks", "evidence_status": "evidence-found"}],
            "citations": [],
            "tool_trace": [],
            "verification": {
                "verified": False,
                "semantic_support_checked": False,
                "currentness_checked": False,
            },
        }


def wait_for_terminal(run_id):
    terminal = {"completed", "failed"}
    for _ in range(100):
        response = client.get(f"/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        if data["status"] in terminal:
            return data
        time.sleep(0.02)
    raise AssertionError("Run did not reach a terminal status")


def test_home_and_health_endpoints():
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["status"] == "healthy"


def test_check_valid_proposal_is_validation_only():
    response = client.post("/check", json=VALID_PROPOSAL)

    assert response.status_code == 200
    assert response.json()["recommendation"] == "specialist-review"
    assert response.json()["status"] == "validated"


def test_rejects_invalid_proposal_and_quarantines_without_agent():
    proposal = {**VALID_PROPOSAL, "plot_area": -10}
    response = client.post("/runs", json=proposal)

    assert response.status_code == 422
    data = response.json()
    assert data["agent_started"] is False
    assert data["quarantine_id"]
    assert any("plot_area" in error["field"] for error in data["field_errors"])

    quarantine = client.get(f"/quarantine/{data['quarantine_id']}")
    assert quarantine.status_code == 200
    assert quarantine.json()["field_errors"]
    assert client.get(f"/runs/{data['quarantine_id']}").status_code == 404


def test_rejects_unknown_fields_and_invalid_categories():
    assert client.post(
        "/check",
        json={**VALID_PROPOSAL, "debug": True},
    ).status_code == 422
    assert client.post(
        "/check",
        json={**VALID_PROPOSAL, "building_use": "warehouse"},
    ).status_code == 422


def test_cross_field_site_area_validation():
    response = client.post(
        "/check",
        json={**VALID_PROPOSAL, "site_width": 5, "site_depth": 10},
    )
    assert response.status_code == 422
    assert response.json()["agent_started"] is False


def test_start_run_persists_result_and_feedback(monkeypatch):
    import agents.workflow

    monkeypatch.setattr(agents.workflow, "compliance_workflow", FakeWorkflow())
    response = client.post("/runs", json=VALID_PROPOSAL)

    assert response.status_code == 202
    submitted = response.json()
    assert submitted["run_id"]
    assert submitted["correlation_id"]
    assert submitted["queue_mode"] == "local"

    result = wait_for_terminal(submitted["run_id"])
    assert result["recommendation"] == "specialist-review"
    assert result["verification"]["semantic_support_checked"] is False

    feedback = client.post(
        f"/runs/{submitted['run_id']}/feedback",
        json={"satisfactory": True, "reason": "Citations are clear."},
    )
    assert feedback.status_code == 201
    assert feedback.json()["satisfactory"] is True
    assert client.get("/feedback/summary").json()["satisfactory"] == 1


def test_failed_workflow_is_not_returned_as_answer(monkeypatch):
    import agents.workflow

    class BrokenWorkflow:
        def invoke(self, state):
            raise RuntimeError("internal detail")

    monkeypatch.setattr(agents.workflow, "compliance_workflow", BrokenWorkflow())
    response = client.post("/runs", json=VALID_PROPOSAL)
    result = wait_for_terminal(response.json()["run_id"])

    assert response.status_code == 202
    assert result["status"] == "failed"
    assert result["recommendation"] == "specialist-review"
    assert "internal detail" not in response.text


def test_unknown_run_returns_404():
    assert client.get("/runs/not-a-run").status_code == 404


def test_correlation_id_is_preserved_and_metrics_render():
    response = client.get("/health", headers={"X-Correlation-ID": "demo-case-01"})
    assert response.headers["X-Correlation-ID"] == "demo-case-01"
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "building_compliance_up 1" in metrics.text
