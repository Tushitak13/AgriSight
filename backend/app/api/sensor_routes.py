from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import DEFAULT_DEVICE_ID
from app.database.database import get_db
from app.schemas.sensor_schema import EnvironmentalStateOut, SensorReadingIn, SensorReadingOut
from app.services.ingestion import sensor_service as svc
from app.services.state.environmental_state import state_for_device

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.post("/readings", response_model=SensorReadingOut, status_code=201)
def post_reading(payload: SensorReadingIn, db: Session = Depends(get_db)):
    try:
        return svc.ingest_reading(db, payload)
    except svc.IngestionError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/latest", response_model=SensorReadingOut)
def latest(device_id: str = DEFAULT_DEVICE_ID, db: Session = Depends(get_db)):
    row = svc.get_latest(db, device_id)
    if not row:
        raise HTTPException(status_code=404, detail="no readings for this device")
    return row


@router.get("/history", response_model=list[SensorReadingOut])
def history(device_id: str = DEFAULT_DEVICE_ID,
            limit: int = Query(100, ge=1, le=1000),
            start: datetime | None = None, end: datetime | None = None,
            db: Session = Depends(get_db)):
    return svc.get_history(db, device_id, limit, start, end)


@router.get("/state", response_model=EnvironmentalStateOut)
def environmental_state(device_id: str = DEFAULT_DEVICE_ID, db: Session = Depends(get_db)):
    state = state_for_device(db, device_id)
    if state is None:
        raise HTTPException(status_code=404, detail="no readings for this device")
    return state
