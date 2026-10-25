"""Advisory-only tomato environmental assessment.

These provisional checks are not a calibrated disease-risk model. The function
reports data quality and broad environmental observations only.
"""
from datetime import datetime, timezone

from app.utils.constants import SENSOR_FIELDS

MAX_READING_AGE_MINUTES = 15


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def assess_tomato_environment(reading, unreliable_inputs=None, now=None) -> dict:
    """Describe environmental context without diagnosing or predicting disease."""
    now = _utc_naive(now or datetime.now(timezone.utc))
    as_of = _utc_naive(reading.device_timestamp)
    age_minutes = max(0.0, (now - as_of).total_seconds() / 60.0)
    missing = [field for field in SENSOR_FIELDS if getattr(reading, field, None) is None]
    unreliable = sorted(set(unreliable_inputs or []))
    range_flags = list(getattr(reading, "range_flags", []) or [])
    stale = age_minutes > MAX_READING_AGE_MINUTES
    warnings, recommendations = [], []

    temperature = getattr(reading, "temperature", None)
    humidity = getattr(reading, "humidity", None)
    if temperature is not None and "temperature" not in unreliable:
        if temperature >= 30:
            warnings.append("Temperature is elevated; monitor plants for heat stress.")
            recommendations.append("Check plants during the warmest part of the day and avoid unnecessary water stress.")
        elif temperature <= 10:
            warnings.append("Temperature is low; monitor plants for cold stress.")
            recommendations.append("Check local growing guidance before taking protective measures against cold.")
    if humidity is not None and "humidity" not in unreliable and humidity >= 85:
        warnings.append("Relative humidity is high; some tomato diseases are favored by prolonged humidity or leaf wetness.")
        recommendations.append("Improve airflow around plants and avoid unnecessarily wetting foliage.")
    if not warnings:
        warnings.append("No warning threshold was triggered by the limited provisional checks; this does not mean disease risk is absent.")
    if missing:
        recommendations.append("Restore or verify missing sensors before relying on the assessment.")
    if unreliable:
        recommendations.append("Check the listed unreliable sensors and their recent readings before using their values.")
    if range_flags:
        recommendations.append("Inspect flagged sensor values and confirm sensor calibration.")
    if stale:
        recommendations.append("Wait for a fresh sensor reading before relying on this assessment.")

    data_status = "limited" if (missing or unreliable or range_flags or stale) else "available"
    return {
        "device_id": reading.device_id,
        "crop": "tomato",
        "as_of": as_of,
        "reading_age_minutes": round(age_minutes, 2),
        "data_status": data_status,
        "missing_inputs": missing,
        "unreliable_inputs": unreliable,
        "range_flags": range_flags,
        "environmental_warnings": warnings,
        "preventive_recommendations": recommendations,
        "disease_probability": None,
        "diagnosis": None,
        "advisory_only": True,
        "actuation_enabled": False,
        "model_validation_status": "provisional_rules_not_validated_for_disease_prediction",
    }
