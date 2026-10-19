
from fastapi.testclient import TestClient

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
    del proposal["plot_area"]

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


def test_start_run_and_retrieve_result():
    response = client.post("/runs", json=VALID_PROPOSAL)

    assert response.status_code == 202

    data = response.json()
    run_id = data["run_id"]

    assert data["status"] == "pending"
    assert run_id in runs

    # FastAPI TestClient executes background tasks before the
    # request finishes, so the stored run should now be processed.
    result = client.get(f"/runs/{run_id}")

    assert result.status_code == 200
    assert result.json()["run_id"] == run_id
    assert result.json()["status"] == "completed"
    assert result.json()["findings"] == []


def test_unknown_run_returns_404():
    response = client.get("/runs/unknown-run-id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found"
