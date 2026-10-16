from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

import pytest
from app.services.reliability.consistency import check_consistency
from app.services.reliability.sensor_reliability import compute_reliability
from tests.conftest import GOOD


def R(**kw):
    base = dict(temperature=29.0, humidity=66.0, soil=40.0, rain=0.0, water=1700.0, light=450.0)
    base.update(kw)
    return NS(**base)


def history(n=12, soil_seq=None):
    soils = soil_seq or [40, 41, 39, 42, 40, 41, 40, 39, 41, 40, 42, 40][:n]
    temps = [28.8, 29.1, 29.0, 29.3, 28.9, 29.2, 29.0, 29.1, 28.8, 29.2, 29.0, 29.1]
    return [R(soil=s, temperature=temps[i % 12], humidity=64 + (i % 3), light=440 + 5 * (i % 4))
            for i, s in enumerate(soils)]


# ---- engine
def test_healthy_sensors_score_high():
    rep = compute_reliability(history() + [R(soil=41)])
    assert rep["summary"]["soil_reliability"] > 0.9
    assert rep["summary"]["overall_sensor_reliability"] > 0.85
    assert not rep["anomaly_detected"]


def test_soil_spike_detected():
    rep = compute_reliability(history() + [R(soil=95)])
    s = rep["sensors"]["soil"]
    assert "spike" in s["flags"] and s["spike_score"] == 0.0
    assert rep["summary"]["soil_reliability"] < 0.75
    assert "soil" in rep["anomalous_sensors"] and rep["anomaly_detected"]


def test_missing_latest_is_zero():
    rep = compute_reliability(history() + [R(rain=None)])
    assert rep["summary"]["rain_reliability"] == 0.0
    assert "missing_latest" in rep["sensors"]["rain"]["flags"]
    assert rep["weakest_sensor"] == "rain"


def test_out_of_range_capped():
    rep = compute_reliability(history() + [R(soil=140)])
    assert rep["summary"]["soil_reliability"] <= 0.2
    assert "out_of_range" in rep["sensors"]["soil"]["flags"]


def test_consistency_penalty():
    assert check_consistency(dict(soil=92, rain=0, temperature=29, humidity=60, light=400))
    rep = compute_reliability(history() + [R(soil=90, rain=0)])
    assert rep["sensors"]["soil"]["consistency_penalty"] > 0
    assert any("inconsistent" in f for f in rep["sensors"]["rain"]["flags"])



def test_flatline_detected():
    rows = [R(soil=40.0) for _ in range(13)]
    rep = compute_reliability(rows)

    # A flatline must be detected and reduce the sensor's reliability.
    assert "flatline" in rep["sensors"]["soil"]["flags"]
    assert rep["summary"]["soil_reliability"] < 0.95

    # A flatline alone is a warning, not automatic exclusion
    # from downstream CRI and similarity calculations.
    assert "soil" not in rep["anomalous_sensors"]


def test_noisy_sensor_less_stable():
    noisy = [10, 70, 20, 80, 15, 75, 25, 65, 30, 60, 20, 70]
    rep = compute_reliability(history(soil_seq=noisy) + [R(soil=50)])
    assert rep["sensors"]["soil"]["stability_score"] < 0.3


def test_first_reading_neutral():
    rep = compute_reliability([R()])
    assert "insufficient_history" in rep["sensors"]["soil"]["flags"]
    assert rep["summary"]["soil_reliability"] == 1.0


def test_rain_onset_not_flagged_as_spike():
    rep = compute_reliability(history() + [R(rain=70)])
    assert "spike" not in rep["sensors"]["rain"]["flags"]


# ---- API
def test_reliability_endpoint(client):
    base = datetime.now(timezone.utc) - timedelta(minutes=30)
    for i, soil in enumerate([40, 41, 39, 42, 40, 41, 95]):
        ts = (base + timedelta(minutes=i)).isoformat()
        client.post("/api/sensors/readings", json={**GOOD, "soil": soil, "timestamp": ts,
                                                   "temperature": 29 + 0.1 * i})
    d = client.get("/api/reliability/latest").json()
    assert d["anomaly_detected"] and "soil" in d["anomalous_sensors"]
    assert "overall_sensor_reliability" in d["summary"]


def test_reliability_404(client):
    assert client.get("/api/reliability/latest?device_id=none").status_code == 404
