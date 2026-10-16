from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import DEFAULT_DEVICE_ID
from app.database.database import get_db
from app.schemas.confidence_schema import ACIResult
from app.services.confidence.aci import aci_for_device

router = APIRouter(prefix="/api/aci", tags=["aci"])


@router.get("/current", response_model=ACIResult)
def current_aci(device_id: str = DEFAULT_DEVICE_ID, include_vision: bool = True,
                db: Session = Depends(get_db)):
    """Adaptive Confidence Index for the device right now: how far the combined evidence
    (sensors, camera, history, recent predictions) can be trusted."""
    result = aci_for_device(db, device_id, include_vision)
    if result is None:
        raise HTTPException(status_code=404, detail="no readings for this device")
    return result
