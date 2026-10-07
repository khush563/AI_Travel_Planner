from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_auto_mode_uses_demo_without_keys():
    assert Settings(demo_mode="auto", openai_api_key="", serper_api_key="").mode == "demo"
    assert Settings(demo_mode="auto", openai_api_key="key", serper_api_key="key").mode == "live"


def test_browser_assets_and_keyless_review_flow(monkeypatch, tmp_path, request_data):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DATABASE_DIR", str(tmp_path))
    client = TestClient(create_app())
    assert client.get("/").status_code == 200
    assert "Plan your escape" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200
    assert client.get("/config").json() == {"mode": "demo"}

    created = client.post("/plan", json=request_data)
    assert created.status_code == 202
    plan_id = created.json()["plan_id"]
    draft = client.get(f"/plan/{plan_id}").json()
    assert draft["requires_review"] is True
    assert draft["draft_itinerary"]["trip_summary"]["mode"] == "demo"
    assert draft["research"]["sources"] == []

    changed = client.post(f"/plan/{plan_id}/review", json={
        "action": "modify", "modifications": {"day": 2, "request": "Add a food tour"},
    }).json()
    assert changed["status"] == "awaiting_review"
    assert changed["draft_itinerary"]["days"][1]["activities"][0]["description"] == "Add a food tour"
    assert client.post(f"/plan/{plan_id}/review", json={"action": "approve"}).json()["status"] == "finalized"
    assert client.get(f"/plan/{plan_id}/final").status_code == 200

