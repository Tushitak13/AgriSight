from datetime import datetime, timedelta, timezone
from tests.conftest import GOOD


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_post_valid_reading(client):
    r = client.post("/api/sensors/readings", json=GOOD)
    assert r.status_code == 201
    d = r.json()
    assert d["soil"] == 37 and d["missing_fields"] == [] and d["range_flags"] == []
    assert d["device_id"] == "esp32-01"


def test_missing_sensor_is_stored_and_flagged(client):
    p = {k: v for k, v in GOOD.items() if k != "rain"}
    d = client.post("/api/sensors/readings", json=p).json()
    assert d["missing_fields"] == ["rain"] and d["rain"] is None


def test_out_of_range_is_stored_and_flagged(client):
    d = client.post("/api/sensors/readings", json={**GOOD, "soil": 140}).json()
    assert d["range_flags"] == ["soil_out_of_range"]


def test_wrong_type_rejected(client):
    assert client.post("/api/sensors/readings", json={**GOOD, "soil": "wet"}).status_code == 422


def test_empty_payload_rejected(client):
    assert client.post("/api/sensors/readings", json={"device_id": "x"}).status_code == 422


def test_future_timestamp_rejected(client):
    ts = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert client.post("/api/sensors/readings", json={**GOOD, "timestamp": ts}).status_code == 422


def test_latest_and_history_order(client):
    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    for i, soil in enumerate([40, 41, 39]):
        ts = (base + timedelta(minutes=i)).isoformat()
        client.post("/api/sensors/readings", json={**GOOD, "soil": soil, "timestamp": ts})
    assert client.get("/api/sensors/latest").json()["soil"] == 39
    h = client.get("/api/sensors/history?limit=2").json()
    assert [x["soil"] for x in h] == [39, 41]


def test_latest_404_when_empty(client):
    assert client.get("/api/sensors/latest?device_id=nope").status_code == 404


def test_devices_are_separate(client):
    client.post("/api/sensors/readings", json={**GOOD, "device_id": "a", "soil": 10})
    client.post("/api/sensors/readings", json={**GOOD, "device_id": "b", "soil": 90})
    assert client.get("/api/sensors/latest?device_id=a").json()["soil"] == 10
