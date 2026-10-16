"""Environmental State Engine: raw readings -> interpretable states (DRY, NO_RAIN, ...).
Inputs whose sensor is unreliable are listed in `unreliable_inputs` so later layers
(ACI, FLAI) do not blindly trust the state derived from them."""
from sqlalchemy.orm import Session

from app.services.ingestion import sensor_service
from app.services.reliability.sensor_reliability import reliability_for_device
from app.utils import constants as K


def classify(field: str, value: float | None) -> str:
    if value is None:
        return "UNKNOWN"
    for upper, label in K.STATE_THRESHOLDS[field]:
        if upper is None or value <= upper:
            return label
    return "UNKNOWN"


def compute_state(values: dict, unreliable: list[str] | None = None) -> dict:
    out = {f"{f}_state": classify(f, values.get(f)) for f in K.SENSOR_FIELDS}
    out["water_constraint"] = out["water_state"] in K.WATER_CONSTRAINT_STATES
    out["unreliable_inputs"] = sorted(unreliable or [])
    return out


def state_for_device(db: Session, device_id: str) -> dict | None:
    latest = sensor_service.get_latest(db, device_id)
    if latest is None:
        return None
    report = reliability_for_device(db, device_id)
    unreliable = [f for f, s in report["sensors"].items() if s["score"] < K.RELIABILITY_LOW]
    state = compute_state({f: getattr(latest, f) for f in K.SENSOR_FIELDS}, unreliable)
    state.update(device_id=device_id, as_of=latest.device_timestamp)
    return state
