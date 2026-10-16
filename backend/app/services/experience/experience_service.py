"""Experience Memory Engine (Module 7).

Handles:
- storing historical experiences
- storing intervention outcomes
- farm-specific history
- similarity-based retrieval
- integration with Phase 4 sensor/state/vision data
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEFAULT_DEVICE_ID
from app.models.experience import Experience
from app.models.vision import VisionObservation

from app.services.similarity.similarity_engine import (
    rank_experiences
)

from app.services.ingestion.sensor_service import (
    get_latest
)

from app.services.state.environmental_state import (
    state_for_device
)

from app.utils.constants import SENSOR_FIELDS


DEFAULT_TOP_K = 5

DEFAULT_THRESHOLD = 0.60


def _utcnow_naive() -> datetime:
    """
    Return current UTC time without timezone info.

    This matches the existing database convention.
    """

    return datetime.now(
        timezone.utc
    ).replace(
        tzinfo=None
    )


def record_experience(
    db: Session,
    *,
    farm_id: str,
    context: dict,
    intervention: dict,
    device_id: str | None = None,
    occurred_at: datetime | None = None,
    source: str = "system",
) -> Experience:

    row = Experience(
        farm_id=farm_id,
        device_id=device_id,
        occurred_at=(
            occurred_at
            or _utcnow_naive()
        ),
        context=context or {},
        intervention=intervention or {},
        source=source,
        created_at=_utcnow_naive(),
    )

    db.add(row)

    db.commit()

    db.refresh(row)

    return row


def record_outcome(
    db: Session,
    experience_id: int,
    *,
    outcome: dict,
    success: bool | None = None,
    score: float | None = None,
    confidence: float | None = None,
) -> Experience | None:

    row = db.get(
        Experience,
        experience_id
    )

    if row is None:
        return None

    row.outcome = outcome or {}

    row.outcome_success = success

    if score is None:
        row.outcome_score = None
    else:
        row.outcome_score = max(
            0.0,
            min(1.0, float(score))
        )

    if confidence is None:
        row.outcome_confidence = None
    else:
        row.outcome_confidence = max(
            0.0,
            min(1.0, float(confidence))
        )

    db.commit()

    db.refresh(row)

    return row


def get_history(
    db: Session,
    farm_id: str,
    *,
    device_id: str | None = None,
    limit: int = 100,
) -> list[Experience]:

    query = select(
        Experience
    ).where(
        Experience.farm_id == farm_id
    )

    if device_id:
        query = query.where(
            Experience.device_id == device_id
        )

    query = (
        query
        .order_by(
            Experience.occurred_at.desc(),
            Experience.id.desc()
        )
        .limit(limit)
    )

    return list(
        db.scalars(query)
    )


def find_similar(
    db: Session,
    farm_id: str,
    context: dict,
    *,
    device_id: str | None = None,
    top_k: int = DEFAULT_TOP_K,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[dict]:

    experiences = get_history(
        db,
        farm_id,
        device_id=device_id,
        limit=1000
    )

    return rank_experiences(
        context,
        experiences,
        top_k=top_k,
        threshold=threshold
    )


def current_context(
    db: Session,
    device_id: str = DEFAULT_DEVICE_ID
) -> dict | None:

    """
    Build a current context using Phase 4 data.

    Sources:
        1. latest sensor reading
        2. environmental state
        3. latest vision observation
    """

    latest = get_latest(
        db,
        device_id
    )

    if latest is None:
        return None

    context = {
        field: getattr(
            latest,
            field
        )
        for field in SENSOR_FIELDS
    }

    state = state_for_device(
        db,
        device_id
    ) or {}

    for key in (
        "soil_state",
        "rain_state",
        "temperature_state",
        "humidity_state",
        "water_state",
        "light_state",
        "water_constraint",
    ):

        if key in state:
            context[key] = state[key]

    vision = db.scalars(
        select(
            VisionObservation
        )
        .where(
            VisionObservation.device_id == device_id
        )
        .order_by(
            VisionObservation.captured_at.desc(),
            VisionObservation.id.desc()
        )
        .limit(1)
    ).first()

    if vision:

        context.update(
            {
                "visual_state": vision.visual_state,
                "prediction": vision.prediction,
                "vision_reliability": vision.vision_reliability,
                "vision_trusted": vision.trusted,
            }
        )

    return context