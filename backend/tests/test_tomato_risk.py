from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.tomato_risk.service import assess_tomato_environment
from tests.conftest import GOOD


def make_reading(**overrides):
    values = {
        "device_id": "agrisight-esp32-01",
        **GOOD,
        "device_timestamp": datetime.now(timezone.utc).replace(tzinfo=None),
        "missing_fields": [],
        "range_flags": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_normal_reading_is_advisory_only():
    result = assess_tomato_environment(make_reading())
    assert result["crop"] == "tomato"
    assert result["data_status"] == "available"
    assert result["disease_probability"] is None
    assert result["diagnosis"] is None
    assert result["advisory_only"] is True
    assert result["actuation_enabled"] is False


def test_high_humidity_gives_preventive_guidance():
    result = assess_tomato_environment(make_reading(humidity=90.0))
    assert any("humidity is high" in item.lower() for item in result["environmental_warnings"])
    assert any("airflow" in item.lower() for item in result["preventive_recommendations"])


def test_missing_sensor_marks_data_limited():
    result = assess_tomato_environment(make_reading(soil=None))
    assert "soil" in result["missing_inputs"]
    assert result["data_status"] == "limited"
    assert any("missing sensors" in item.lower() for item in result["preventive_recommendations"])


def test_unreliable_temperature_is_not_used_for_warning():
    result = assess_tomato_environment(make_reading(temperature=40.0), unreliable_inputs=["temperature"])
    assert not any("temperature is elevated" in item.lower() for item in result["environmental_warnings"])
    assert "temperature" in result["unreliable_inputs"]
    assert result["data_status"] == "limited"


def test_stale_reading_marks_data_limited():
    old = (datetime.now(timezone.utc) - timedelta(minutes=30)).replace(tzinfo=None)
    result = assess_tomato_environment(make_reading(device_timestamp=old))
    assert result["data_status"] == "limited"
    assert any("fresh sensor reading" in item.lower() for item in result["preventive_recommendations"])


def test_range_flags_are_reported():
    result = assess_tomato_environment(make_reading(range_flags=["temperature_out_of_range"]))
    assert result["range_flags"] == ["temperature_out_of_range"]
    assert result["data_status"] == "limited"
    assert any("calibration" in item.lower() for item in result["preventive_recommendations"])


def test_live_endpoint_returns_404_without_sensor_data(client):
    response = client.get("/api/tomato-risk/current?device_id=missing-device")
    assert response.status_code == 404


def test_live_endpoint_is_advisory_only_and_explains_flais_calibration(client):
    response = client.post("/api/sensors/readings", json={**GOOD, "device_id": "tomato-test"})
    assert response.status_code == 201
    result = client.get("/api/tomato-risk/current?device_id=tomato-test")
    assert result.status_code == 200
    body = result.json()
    assert body["advisory_only"] is True
    assert body["actuation_enabled"] is False
    assert body["disease_probability"] is None
    assert body["flai_integration_status"] == "not_calibrated"
    assert "vision_context" in body
