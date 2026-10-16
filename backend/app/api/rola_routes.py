
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.experience import Experience
from app.models.recalibration import RecalibrationAssessment
from app.services.learning.rola_engine import (
    assess_response,
    summarize_error_history,
)
from app.schemas.rola_schema import (
    ROLAAssessRequest,
    ROLAAssessResponse,
    ROLASummaryRequest,
    ROLASummaryResponse,
)

router = APIRouter(prefix="/api/rola", tags=["ROLA"])


def _db_timestamp(value: str | None) -> datetime | None:
    """Convert valid ISO timestamps to naive UTC for database storage."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


@router.post("/assess", response_model=ROLAAssessResponse)
def assess_rola_response(
    payload: ROLAAssessRequest,
    db: Session = Depends(get_db),
):
    """Assess a response; persist only when experience_id is supplied."""
    assessment_input = payload.model_dump(exclude={"experience_id"})
    result = assess_response(**assessment_input)

    # Backward compatibility: callers without an experience ID remain stateless.
    if payload.experience_id is None:
        return result

    experience = db.get(Experience, payload.experience_id)
    if experience is None:
        raise HTTPException(status_code=404, detail="experience not found")

    if experience.source != "real":
        raise HTTPException(
            status_code=409,
            detail="ROLA assessments can only be linked to real experiences",
        )

    if experience.outcome_status is None:
        raise HTTPException(
            status_code=409,
            detail="experience must have a recorded outcome before assessment persistence",
        )

    existing = db.scalar(
        select(RecalibrationAssessment).where(
            RecalibrationAssessment.experience_id == experience.id
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="ROLA assessment already recorded for this experience",
        )

    predicted_unit = payload.predicted_unit
    observed_unit = payload.observed_unit
    compatible_unit = (
        predicted_unit
        if predicted_unit
        and observed_unit
        and predicted_unit.strip().lower() == observed_unit.strip().lower()
        else None
    )

    row = RecalibrationAssessment(
        experience_id=experience.id,
        model_version=None,
        predicted_value=payload.predicted_value,
        observed_value=payload.observed_value,
        predicted_at=_db_timestamp(payload.predicted_at),
        observed_at=_db_timestamp(payload.observed_at),
        unit=compatible_unit,
        predicted_unit=predicted_unit,
        observed_unit=observed_unit,
        source_type=payload.source_type,
        value_kind=payload.value_kind,
        predicted_depth_cm=payload.predicted_depth_cm,
        observed_depth_cm=payload.observed_depth_cm,
        independent_of_target_sensor=payload.independent_of_target_sensor,
        event_recorded=payload.event_recorded,
        event_timing_trustworthy=payload.event_timing_trustworthy,
        model_calibrated_for_context=payload.model_calibrated_for_context,
        observation_quality_ok=payload.observation_quality_ok,
        comparable=result["comparable"],
        attribution_eligible=result["attribution_eligible"],
        signed_error=result["signed_error"],
        absolute_error=result["absolute_error"],
        reasons=result["reasons"],
        assessed_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    try:
        db.add(row)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="ROLA assessment conflicts with an existing audit record",
        ) from exc
    except SQLAlchemyError:
        db.rollback()
        raise

    return result


@router.post("/summarize-errors", response_model=ROLASummaryResponse)
def summarize_rola_errors(payload: ROLASummaryRequest):
    """Summarize numeric errors for diagnostics only."""
    return summarize_error_history(payload.errors)
