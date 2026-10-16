from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import DEFAULT_DEVICE_ID
from app.database.database import get_db
from app.services.confidence.aci import aci_for_device
from app.schemas.vision_schema import TriggerDecision, VisionObservationOut
from app.services.reliability.sensor_reliability import reliability_for_device
from app.services.vision import vision_service as svc
from app.services.vision.trigger_engine import decide_trigger
from app.utils.constants import MAX_IMAGE_BYTES

router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.get("/trigger", response_model=TriggerDecision)
def check_trigger(device_id: str = DEFAULT_DEVICE_ID, db: Session = Depends(get_db)):
    """Should the camera run right now? Based on sensor reliability, ACI and whether the
    situation is unfamiliar. ACI is computed WITHOUT camera evidence: deciding whether to
    use the camera cannot depend on the camera."""
    report = reliability_for_device(db, device_id)
    aci = aci_for_device(db, device_id, include_vision=False, report=report) if report else None
    decision = decide_trigger(report, aci=aci["aci"] if aci else None,
                              unexplained_condition=bool(aci and aci["novel_condition"]))
    decision["aci"] = aci["aci"] if aci else None
    return decision


@router.post("/analyze", response_model=VisionObservationOut, status_code=201)
def analyze(file: UploadFile = File(...), device_id: str = Form(DEFAULT_DEVICE_ID),
            db: Session = Depends(get_db)):
    raw = file.file.read(MAX_IMAGE_BYTES + 1)
    try:
        return svc.analyze_upload(db, device_id, raw)
    except svc.VisionError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/latest", response_model=VisionObservationOut)
def latest(device_id: str = DEFAULT_DEVICE_ID, db: Session = Depends(get_db)):
    row = svc.get_latest_observation(db, device_id)
    if not row:
        raise HTTPException(status_code=404, detail="no vision observations for this device")
    return row


@router.get("/history", response_model=list[VisionObservationOut])
def history(device_id: str = DEFAULT_DEVICE_ID, limit: int = Query(50, ge=1, le=500),
            db: Session = Depends(get_db)):
    return svc.get_observation_history(db, device_id, limit)
