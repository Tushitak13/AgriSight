from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import DEFAULT_DEVICE_ID, RELIABILITY_WINDOW
from app.database.database import get_db
from app.schemas.reliability_schema import ReliabilityReport
from app.services.reliability.sensor_reliability import reliability_for_device

router = APIRouter(prefix="/api/reliability", tags=["reliability"])


@router.get("/latest", response_model=ReliabilityReport)
def latest_reliability(device_id: str = DEFAULT_DEVICE_ID,
                       window: int = Query(RELIABILITY_WINDOW, ge=5, le=200),
                       db: Session = Depends(get_db)):
    report = reliability_for_device(db, device_id, window)
    if report is None:
        raise HTTPException(status_code=404, detail="no readings for this device")
    return report
