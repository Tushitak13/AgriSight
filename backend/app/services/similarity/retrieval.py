"""Finds similar past experiences for a device (farm-specific: only that device's own history)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.experience import Experience
from app.services.ingestion import sensor_service
from app.services.reliability.sensor_reliability import reliability_for_device
from app.services.similarity import similarity_engine as eng
from app.utils import constants as K


def find_similar(db: Session, device_id: str, condition: dict, k: int, min_similarity: float,
                 only_with_outcome: bool = False) -> dict:
    query = {f: v for f, v in condition.items() if f in K.SENSOR_FIELDS and v is not None}
    q = select(Experience).where(Experience.device_id == device_id)
    if only_with_outcome:
        q = q.where(Experience.outcome_status.is_not(None))
    q = q.order_by(Experience.created_at.desc(), Experience.id.desc()).limit(K.MAX_EXPERIENCES_SCANNED)
    experiences = list(db.scalars(q))

    matches = eng.rank(query, experiences, k, min_similarity)
    return dict(
        device_id=device_id, query=query,
        n_experiences_searched=len(experiences), n_matches=len(matches),
        has_history=len(matches) > 0,
        historical_similarity=eng.historical_similarity(matches),
        matches=matches,
        intervention_summary=eng.summarize_interventions(matches),
    )


def find_similar_to_current(db: Session, device_id: str, k: int, min_similarity: float,
                            only_with_outcome: bool = False, exclude_unreliable: bool = True,
                            report: dict | None = None):
    """Similar experiences for the device's latest reading. Sensors the reliability engine
    distrusts are left out of the query so a faulty value cannot drive retrieval.
    Returns (result, excluded_fields), or None when the device has no readings."""
    latest = sensor_service.get_latest(db, device_id)
    if latest is None:
        return None
    excluded: list[str] = []
    if exclude_unreliable:
        report = report or reliability_for_device(db, device_id)
        excluded = sorted(report["anomalous_sensors"])      # low score OR spike OR out of range
    condition = {f: getattr(latest, f) for f in K.SENSOR_FIELDS if f not in excluded}
    return find_similar(db, device_id, condition, k, min_similarity, only_with_outcome), excluded
