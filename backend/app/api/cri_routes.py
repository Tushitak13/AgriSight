from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import DEFAULT_DEVICE_ID
from app.database.database import get_db
from app.schemas.confidence_schema import CRIResult
from app.services.resilience.cri import cri_for_device

router = APIRouter(prefix="/api/cri", tags=["cri"])


@router.get("/current", response_model=CRIResult)
def current_cri(device_id: str = DEFAULT_DEVICE_ID, db: Session = Depends(get_db)):
    """Crop Resilience Index (project-specific): estimated ability to tolerate and recover from stress."""
    result = cri_for_device(db, device_id)
    if result is None:
        raise HTTPException(status_code=404, detail="no readings for this device")
    return result
