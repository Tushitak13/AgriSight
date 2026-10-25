from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import DEFAULT_DEVICE_ID
from app.database.database import get_db
from app.services.ingestion import sensor_service
from app.services.reliability.sensor_reliability import reliability_for_device
from app.services.tomato_risk.service import assess_tomato_environment
from app.services.vision import vision_service
from app.utils import constants as K

router = APIRouter(prefix="/api/tomato-risk", tags=["tomato-risk"])


def _vision_context(db: Session, device_id: str):
    row = vision_service.get_latest_observation(db, device_id)
    if row is None:
        return None
    captured = row.captured_at
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if captured.tzinfo is not None:
        captured = captured.astimezone(timezone.utc).replace(tzinfo=None)
    age_minutes = max(0.0, (now - captured).total_seconds() / 60.0)
    placeholder = str(row.model_name or "").startswith("placeholder_")
    return {
        "captured_at": captured,
        "age_minutes": round(age_minutes, 2),
        "model_name": row.model_name,
        "visual_state": row.visual_state,
        "prediction": row.prediction,
        "model_confidence": row.model_confidence,
        "trusted": bool(row.trusted),
        "is_placeholder_model": placeholder,
        "interpretation": (
            "Placeholder vegetation heuristic only; not a tomato disease classifier."
            if placeholder else
            "Model output is shown as recorded; disease validity depends on the model's training and validation."
        ),
    }


@router.get("/current")
def current_tomato_risk(
    device_id: str = Query(default=DEFAULT_DEVICE_ID, min_length=1, max_length=64),
    db: Session = Depends(get_db),
):
    """Return environmental warnings plus clearly qualified latest vision context."""
    reading = sensor_service.get_latest(db, device_id)
    if reading is None:
        raise HTTPException(status_code=404, detail="no readings for this device")

    report = reliability_for_device(db, device_id)
    unreliable = []
    if report is not None:
        unreliable = [
            field for field, details in report["sensors"].items()
            if details["score"] < K.RELIABILITY_LOW
        ]
    result = assess_tomato_environment(reading, unreliable_inputs=unreliable)
    result["vision_context"] = _vision_context(db, device_id)
    result["flai_integration_status"] = "not_calibrated"
    result["flai_integration_note"] = (
        "Environmental observations and image observations are exposed together for review, "
        "but they are not passed as calibrated disease evidence to FLAI. Calibrated likelihoods, "
        "a validated tomato classifier, and crop/threat-specific action utilities are required first."
    )
    return result
