"""Event-Triggered Vision: run the camera only when sensor evidence is weak or suspicious.
Pure function; later phases feed in `aci` (Phase 6) and `unexplained_condition` (Phase 5)."""
from app.utils import constants as K


def decide_trigger(sensor_report: dict | None, aci: float | None = None,
                   unexplained_condition: bool = False) -> dict:
    reasons: list[str] = []
    overall = None
    if sensor_report is None:
        reasons.append("no_sensor_data")
    else:
        overall = sensor_report["summary"]["overall_sensor_reliability"]
        if overall < K.TRIGGER_SENSOR_RELIABILITY_MIN:
            reasons.append("low_sensor_reliability")
        if sensor_report["anomaly_detected"]:
            reasons.append("sensor_anomaly")
        if sensor_report["consistency_findings"]:
            reasons.append("sensor_disagreement")
    if aci is not None and aci < K.TRIGGER_ACI_MIN:
        reasons.append("low_aci")
    if unexplained_condition:
        reasons.append("unexplained_condition")
    return dict(trigger=bool(reasons), reasons=reasons, overall_sensor_reliability=overall,
                anomalous_sensors=(sensor_report or {}).get("anomalous_sensors", []))
