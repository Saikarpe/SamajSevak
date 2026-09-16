from fastapi.testclient import TestClient

from app.main import app
from app.ml.engine import engine


def test_critical_case_is_prioritised():
    a = engine.analyze("Live electric wire fallen near the school in Kothrud, children in danger, very dangerous!")
    assert a["category"] == "Electricity"
    assert a["priority_level"] in ("Critical", "High")
    assert a["ward"] == "Kothrud"
    assert a["recommendation"]["action_plan"]


def test_low_priority_case():
    a = engine.analyze("Illegal hoardings and banners near the park in Baner")
    assert a["category"] == "Encroachment"
    assert a["priority_level"] in ("Low", "Medium")


def test_api_flow():
    with TestClient(app) as c:
        g = c.post("/api/grievances", json={"text": "Garbage not collected near the market in Wakad for 5 days, stinking"}).json()
        assert g["id"].startswith("SS-")
        assert c.patch(f"/api/grievances/{g['id']}", json={"status": "Resolved", "note": "Spot cleared"}).json()["status"] == "Resolved"
        assert c.post(f"/api/grievances/{g['id']}/draft").json()["text"]
        assert c.get("/api/stats").status_code == 200
        assert isinstance(c.get("/api/alerts").json(), list)
