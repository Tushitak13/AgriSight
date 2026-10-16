"""Experience Memory (Module 7): store condition -> decision -> intervention -> outcome records."""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import DEFAULT_DEVICE_ID
from app.models.experience import Experience
from app.schemas.experience_schema import ExperienceCreate, OutcomeIn
from app.services.ingestion.sensor_service import utcnow
from app.services.state.environmental_state import classify


class ExperienceNotFound(LookupError):
    pass


class OutcomeAlreadyRecorded(ValueError):
    pass


def _apply_outcome(row: Experience, outcome: OutcomeIn) -> None:
    after = outcome.after.as_dict() if outcome.after else None
    before_soil = row.condition.get("soil")
    row.outcome_status = outcome.status
    row.outcome_condition = after
    row.soil_change = (round(after["soil"] - before_soil, 2)
                       if after and "soil" in after and before_soil is not None else None)
    row.outcome_recorded_at = utcnow()


def create_experience(db: Session, payload: ExperienceCreate) -> Experience:
    condition = payload.condition.as_dict()
    row = Experience(
        device_id=payload.device_id or DEFAULT_DEVICE_ID, created_at=utcnow(), source=payload.source,
        condition=condition,
        condition_states={f"{f}_state": classify(f, v) for f, v in condition.items()},
        decision=payload.decision, intervention=payload.intervention,
        expected_soil_change=payload.expected_soil_change,
    )
    if payload.outcome is not None:
        _apply_outcome(row, payload.outcome)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_experience(db: Session, experience_id: int) -> Experience:
    row = db.get(Experience, experience_id)
    if row is None:
        raise ExperienceNotFound(f"experience {experience_id} not found")
    return row


def record_outcome(db: Session, experience_id: int, outcome: OutcomeIn) -> Experience:
    """An outcome can be recorded once. Overwriting it later would double-count the same
    result when the Phase 8 recalibration engine learns from it."""
    row = get_experience(db, experience_id)
    if row.outcome_status is not None:
        raise OutcomeAlreadyRecorded("outcome already recorded for this experience")
    _apply_outcome(row, outcome)
    db.commit()
    db.refresh(row)
    return row


def list_experiences(db: Session, device_id: str, limit: int = 100, intervention: str | None = None,
                     has_outcome: bool | None = None, source: str | None = None) -> list[Experience]:
    q = select(Experience).where(Experience.device_id == device_id)
    if intervention:
        q = q.where(Experience.intervention == intervention)
    if has_outcome is True:
        q = q.where(Experience.outcome_status.is_not(None))
    elif has_outcome is False:
        q = q.where(Experience.outcome_status.is_(None))
    if source:
        q = q.where(Experience.source == source)
    q = q.order_by(Experience.created_at.desc(), Experience.id.desc()).limit(limit)
    return list(db.scalars(q))


def delete_seed_experiences(db: Session, device_id: str) -> int:
    """Removes ONLY synthetic (source='seed') rows; real experiences can never be deleted this way."""
    res = db.execute(delete(Experience).where(Experience.device_id == device_id,
                                              Experience.source == "seed"))
    db.commit()
    return res.rowcount or 0
