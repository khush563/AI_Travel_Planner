from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import FailingSearch


def test_api_lifecycle(service_factory, request_data):
    client = TestClient(create_app(service_factory()))
    response = client.post("/plan", json=request_data)
    assert response.status_code == 202
    assert response.json()["status"] == "researching"
    plan_id = response.json()["plan_id"]
    current = client.get(f"/plan/{plan_id}")
    assert current.status_code == 200
    assert current.json()["requires_review"] is True
    assert current.json()["draft_itinerary"]["days"]
    assert client.get(f"/plan/{plan_id}/final").status_code == 409
    reviewed = client.post(f"/plan/{plan_id}/review", json={"action": "approve"})
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "finalized"
    assert client.get(f"/plan/{plan_id}/final").status_code == 200
    assert client.post(f"/plan/{plan_id}/review", json={"action": "approve"}).status_code == 409


def test_validation_and_missing_plan(service_factory, request_data):
    client = TestClient(create_app(service_factory()))
    assert client.get("/plan/missing").status_code == 404
    assert client.post("/plan/missing/review", json={"action": "approve"}).status_code == 404
    assert client.get("/plan/missing/final").status_code == 404
    assert client.post("/plan", json={**request_data, "budget_max": -1}).status_code == 422
    assert client.post("/plan", json={**request_data, "end_date": "2020-01-01"}).status_code == 422
    assert client.post("/plan/missing/review", json={"action": "reject"}).status_code == 422


def test_external_failure_is_recorded_without_leaking_exception(service_factory, request_data):
    client = TestClient(create_app(service_factory(FailingSearch())))
    response = client.post("/plan", json=request_data)
    plan_id = response.json()["plan_id"]
    status = client.get(f"/plan/{plan_id}").json()
    assert status["status"] == "failed"
    assert "external search unavailable" not in status["error"]

