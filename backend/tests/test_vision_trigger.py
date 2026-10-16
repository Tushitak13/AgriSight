import io
from datetime import datetime, timedelta, timezone

from app.services.vision.trigger_engine import decide_trigger
from app.utils.sample_images import make_images
from tests.conftest import GOOD

IMGS = make_images()


def jpg_bytes(name):
    buf = io.BytesIO()
    IMGS[name].save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def report(overall=0.95, anomaly=False, findings=None, anomalous=None):
    return dict(summary={"overall_sensor_reliability": overall}, anomaly_detected=anomaly,
                consistency_findings=findings or [], anomalous_sensors=anomalous or [])


# ---- trigger engine (pure)
def test_no_trigger_when_evidence_good():
    d = decide_trigger(report())
    assert d["trigger"] is False and d["reasons"] == []


def test_low_reliability_triggers():
    assert "low_sensor_reliability" in decide_trigger(report(overall=0.5))["reasons"]


def test_anomaly_and_disagreement_trigger():
    d = decide_trigger(report(anomaly=True, findings=[{"rule": "x"}], anomalous=["soil"]))
    assert d["trigger"] and {"sensor_anomaly", "sensor_disagreement"} <= set(d["reasons"])


def test_low_aci_and_unexplained_trigger():
    assert decide_trigger(report(), aci=0.4)["reasons"] == ["low_aci"]
    assert decide_trigger(report(), unexplained_condition=True)["reasons"] == ["unexplained_condition"]
    assert decide_trigger(report(), aci=0.9)["trigger"] is False


def test_no_data_triggers():
    assert decide_trigger(None)["reasons"] == ["no_sensor_data"]


# ---- API
def _post_series(client, last_soil):
    base = datetime.now(timezone.utc) - timedelta(minutes=30)
    for i, soil in enumerate([40, 41, 39, 42, 40, 41, last_soil]):
        client.post("/api/sensors/readings", json={
            **GOOD, "soil": soil, "temperature": 29 + 0.1 * i,
            "timestamp": (base + timedelta(minutes=i)).isoformat()})


def test_trigger_endpoint_quiet_then_fires(client):
    _post_series(client, 41)
    assert client.get("/api/vision/trigger").json()["trigger"] is False
    client.post("/api/sensors/readings", json={**GOOD, "soil": 95})
    d = client.get("/api/vision/trigger").json()
    assert d["trigger"] is True and "sensor_anomaly" in d["reasons"]


def test_analyze_good_image(client):
    r = client.post("/api/vision/analyze", files={"file": ("a.jpg", jpg_bytes("stressed"), "image/jpeg")})
    assert r.status_code == 201
    d = r.json()
    assert d["prediction"] == "stressed" and d["trusted"] is True
    assert d["effective_confidence"] > 0.8
    assert client.get("/api/vision/latest").json()["id"] == d["id"]


def test_analyze_blurry_image_untrusted(client):
    d = client.post("/api/vision/analyze",
                    files={"file": ("b.jpg", jpg_bytes("blurry"), "image/jpeg")}).json()
    assert d["model_confidence"] > 0.8          # model is confident...
    assert d["trusted"] is False                # ...but evidence is not trusted
    assert d["effective_confidence"] < 0.5
    assert "blurry" in d["quality"]["issues"]


def test_analyze_rejects_non_image(client):
    r = client.post("/api/vision/analyze", files={"file": ("x.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 422


def test_history_and_404(client):
    assert client.get("/api/vision/latest?device_id=zzz").status_code == 404
    for n in ("healthy", "dark"):
        client.post("/api/vision/analyze", files={"file": (f"{n}.jpg", jpg_bytes(n), "image/jpeg")})
    h = client.get("/api/vision/history").json()
    assert len(h) == 2 and h[0]["visual_state"] != h[1]["visual_state"]
