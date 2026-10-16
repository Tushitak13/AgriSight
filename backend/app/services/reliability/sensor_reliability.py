
"""Sensor Reliability Engine.
Per sensor: range + spike (median/MAD) + stability (+flatline) + completeness,
then cross-sensor consistency penalties, then a weighted overall score.
"""
from sqlalchemy.orm import Session

from app.config import RELIABILITY_WINDOW
from app.services.ingestion import sensor_service
from app.services.reliability.anomaly_detection import (
    is_flatline,
    population_std,
    robust_z,
    spike_score,
)
from app.services.reliability.consistency import check_consistency
from app.utils import constants as K


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def evaluate_sensor(field: str, values: list[float | None]) -> dict:
    """Evaluate one sensor's chronological values, newest last."""
    prof = K.SENSOR_PROFILE[field]
    lo, hi = K.NOMINAL_RANGES[field]
    span = hi - lo
    latest = values[-1]
    present = [v for v in values if v is not None]
    completeness = len(present) / len(values)
    flags: list[str] = []

    if latest is None:
        return dict(
            score=0.0,
            range_score=0.0,
            spike_score=0.0,
            stability_score=0.0,
            completeness_score=round(completeness, 3),
            consistency_penalty=0.0,
            flags=["missing_latest"],
            latest=None,
        )

    range_ok = 1.0 if lo <= latest <= hi else 0.0
    if not range_ok:
        flags.append("out_of_range")

    history = [v for v in values[:-1] if v is not None]
    spike = stability = 1.0

    if len(history) < K.MIN_HISTORY_FOR_STATS:
        flags.append("insufficient_history")
    else:
        if prof["spike"]:
            z = robust_z(latest, history, scale_floor=0.01 * span)
            spike = spike_score(z)
            if z > K.SPIKE_Z_THRESHOLD:
                flags.append("spike")

        if prof["vol_cap"]:
            std = population_std(history)
            stability = _clamp(
                1 - std / (prof["vol_cap"] * span)
            )
            if std > 0.5 * prof["vol_cap"] * span:
                flags.append("unstable")

        if prof["flatline"] and is_flatline(
            history, latest, K.FLATLINE_MIN_POINTS
        ):
            stability = min(stability, 0.3)
            flags.append("flatline")

    w = K.COMPONENT_WEIGHTS
    score = (
        w["range"] * range_ok
        + w["spike"] * spike
        + w["stability"] * stability
        + w["completeness"] * completeness
    )

    if not range_ok:
        score = min(score, K.OUT_OF_RANGE_CAP)

    return dict(
        score=score,
        range_score=range_ok,
        spike_score=spike,
        stability_score=stability,
        completeness_score=completeness,
        consistency_penalty=0.0,
        flags=flags,
        latest=latest,
    )


def compute_reliability(readings: list) -> dict:
    """Compute sensor reliability from chronological readings."""
    if not readings:
        raise ValueError("no readings")

    sensors = {
        field: evaluate_sensor(
            field, [getattr(reading, field) for reading in readings]
        )
        for field in K.SENSOR_FIELDS
    }

    # Apply cross-sensor consistency penalties to present, in-range values.
    latest_vals = {
        field: sensor["latest"] if sensor["range_score"] else None
        for field, sensor in sensors.items()
    }
    findings = check_consistency(latest_vals)

    for finding in findings:
        for field in finding["sensors"]:
            sensors[field]["consistency_penalty"] += finding["penalty"]
            sensors[field]["flags"].append(
                f"inconsistent:{finding['rule']}"
            )

    for sensor in sensors.values():
        sensor["score"] = round(
            _clamp(sensor["score"] - sensor["consistency_penalty"]),
            3,
        )
        for key in (
            "range_score",
            "spike_score",
            "stability_score",
            "completeness_score",
            "consistency_penalty",
        ):
            sensor[key] = round(sensor[key], 3)
        sensor.pop("latest")

    total_weight = sum(
        K.SENSOR_PROFILE[field]["weight"] for field in K.SENSOR_FIELDS
    )
    overall = sum(
        K.SENSOR_PROFILE[field]["weight"] * sensors[field]["score"]
        for field in K.SENSOR_FIELDS
    ) / total_weight

    # Flatline remains a sensor-quality warning, but does not by itself
    # automatically exclude a field from CRI or similarity calculations.
    anomalous = [
        field
        for field, sensor in sensors.items()
        if sensor["score"] < K.RELIABILITY_LOW
        or any(
            flag in ("spike", "out_of_range")
            for flag in sensor["flags"]
        )
    ]

    summary = {
        f"{field}_reliability": sensor["score"]
        for field, sensor in sensors.items()
    }
    summary["overall_sensor_reliability"] = round(overall, 3)

    return dict(
        summary=summary,
        sensors=sensors,
        consistency_findings=findings,
        weakest_sensor=min(
            sensors, key=lambda field: sensors[field]["score"]
        ),
        anomalous_sensors=anomalous,
        anomaly_detected=bool(anomalous),
        window_size=len(readings),
    )


def reliability_for_device(
    db: Session,
    device_id: str,
    window: int = RELIABILITY_WINDOW,
):
    """Load recent readings and calculate reliability for one device."""
    rows = sensor_service.get_history(db, device_id, limit=window)
    if not rows:
        return None

    rows.reverse()  # Convert newest-first results to chronological order.
    report = compute_reliability(rows)
    report.update(
        device_id=device_id,
        as_of=rows[-1].device_timestamp,
    )
    return report
