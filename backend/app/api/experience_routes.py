from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import DEFAULT_DEVICE_ID
from app.database.database import get_db
from app.schemas.experience_schema import ExperienceCreate, ExperienceOut, OutcomeIn
from app.services.memory import experience_service as svc

router = APIRouter(prefix="/api/experiences", tags=["experiences"])


@router.post("", response_model=ExperienceOut, status_code=201)
def create_experience(payload: ExperienceCreate, db: Session = Depends(get_db)):
    return svc.create_experience(db, payload)


@router.get("", response_model=list[ExperienceOut])
def list_experiences(device_id: str = DEFAULT_DEVICE_ID,
                     limit: int = Query(100, ge=1, le=1000),
                     intervention: str | None = None,
                     has_outcome: bool | None = None,
                     source: str | None = Query(None, pattern="^(real|seed)$"),
                     db: Session = Depends(get_db)):
    return svc.list_experiences(db, device_id, limit, intervention, has_outcome, source)


@router.delete("/seed")
def delete_seed_data(device_id: str = DEFAULT_DEVICE_ID, db: Session = Depends(get_db)):
    """Dev helper: delete synthetic seed experiences only."""
    return {"deleted": svc.delete_seed_experiences(db, device_id)}


@router.get("/{experience_id}", response_model=ExperienceOut)
def get_experience(experience_id: int, db: Session = Depends(get_db)):
    try:
        return svc.get_experience(db, experience_id)
    except svc.ExperienceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{experience_id}/outcome", response_model=ExperienceOut)
def record_outcome(experience_id: int, outcome: OutcomeIn, db: Session = Depends(get_db)):
    try:
        return svc.record_outcome(db, experience_id, outcome)
    except svc.ExperienceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except svc.OutcomeAlreadyRecorded as e:
        raise HTTPException(status_code=409, detail=str(e))
