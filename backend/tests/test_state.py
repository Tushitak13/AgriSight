from datetime import datetime, timedelta, timezone

from app.services.state.environmental_state import classify, compute_state
from tests.conftest import GOOD


def test_classify_examples_from_design():
    assert classify("soil", 32) == "DRY"
    assert classify("rain", 0) == "NO_RAIN"
    assert classify("temperature", 29) == "NORMAL"
    assert classify("water", 1700) == "SUFFICIENT"
    assert classify("soil", None) == "UNKNOWN"


def test_boundaries():
    assert classify("soil", 20) == "CRITICALLY_DRY"
    assert classify("soil", 20.1) == "DRY"
    assert classify("soil", 90) == "SATURATED"
    assert classify("rain", 80) == "HEAVY_RAIN"


def test_water_constraint():
    assert compute_state({"water": 300})["water_constraint"] is True
    assert compute_state({"water": 800})["water_constraint"] is True
    assert compute_state({"water": 1700})["water_constraint"] is False


def test_state_endpoint_marks_unreliable_inputs(client):
    base = datetime.now(timezone.utc) - timedelta(minutes=30)
    for i, soil in enumerate([40, 41, 39, 42, 40, 41, 95]):
        client.post("/api/sensors/readings", json={
            **GOOD, "soil": soil, "temperature": 29 + 0.1 * i,
            "timestamp": (base + timedelta(minutes=i)).isoformat()})
    d = client.get("/api/sensors/state").json()
    assert d["soil_state"] == "SATURATED" and d["rain_state"] == "NO_RAIN"
    assert d["water_constraint"] is False
    assert "soil" in d["unreliable_inputs"]


def test_state_404(client):
    assert client.get("/api/sensors/state?device_id=none").status_code == 404
