
"""ACI - Adaptive Confidence Index (Module 11).

A project-specific index, not an established metric.

ACI is the weighted mean of AVAILABLE evidence components, with weights
renormalised to account for missing evidence.

Components:
- sensor_reliability: overall sensor reliability
- vision_reliability: image-quality reliability of the latest fresh camera observation
- prediction_confidence: model confidence adjusted for image reliability
- historical_similarity: support from similar past experiences
- recent_behaviour: consistency of recent trusted vision predictions

Missing evidence is skipped rather than treated as zero or perfect.
Cold-start farms and low-coverage evidence cannot reach HIGH confidence.
"""

from collections import Counter
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.experience import Experience
from app.services.ingestion.sensor_service import utcnow, get_latest, get_history
from app.services.reliability.sensor_reliability import reliability_for_device
from app.services.confidence.evidence_decay import age_hours, decay_factor
from app.services.confidence.mahalanobis import mahalanobis_novelty
from app.services.similarity.retrieval import find_similar_to_current
from app.services.vision import vision_service
from app.utils import constants as K


def _clamp(x: float) -> float:
    """Clamp a numeric value to the inclusive [0, 1] range."""
    return max(0.0, min(1.0, float(x)))


def aci_level(aci: float) -> str:
    """Convert an ACI score into a confidence level."""
    return "HIGH" if aci >= K.ACI_HIGH else "LOW" if aci < K.ACI_LOW else "MEDIUM"


def prediction_consistency(observations) -> float | None:
    """Return the share of recent trusted predictions matching the most common label.

    Observations must be ordered newest first. Untrusted predictions are ignored.
    Returns None when fewer than two trusted predictions are available.
    """
    labels = [
        observation.prediction
        for observation in observations
        if observation.trusted
    ][:K.ACI_BEHAVIOUR_WINDOW]

    if len(labels) < 2:
        return None

    return Counter(labels).most_common(1)[0][1] / len(labels)


def compute_aci(
    sensor_reliability: float,
    historical_similarity: float,
    farm_has_history: bool,
    vision_reliability: float | None = None,
    prediction_confidence: float | None = None,
    recent_behaviour: float | None = None,
    evidence_freshness: dict[str, float] | None = None,
) -> dict:
    """Fuse available evidence into an ACI result.

    Evidence freshness reduces a component's effective weight without changing
    its underlying value. Missing components are skipped and the remaining
    weights are renormalised.

    ACI is capped below HIGH when:
    - the farm has no experience history (cold start), or
    - freshness-adjusted evidence coverage is below the configured minimum.

    Omitting evidence_freshness preserves the original pure-fusion behaviour
    apart from the explicit confidence-coverage safeguard.
    """
    values = {
        "sensor_reliability": sensor_reliability,
        "vision_reliability": vision_reliability,
        "prediction_confidence": prediction_confidence,
        "historical_similarity": (
            historical_similarity if farm_has_history else None
        ),
        "recent_behaviour": recent_behaviour,
    }

    values = {
        key: None if value is None else _clamp(value)
        for key, value in values.items()
    }

    freshness = {
        key: _clamp(value)
        for key, value in (evidence_freshness or {}).items()
    }

    # Only available components with nonzero freshness contribute.
    avail = {
        key: value
        for key, value in values.items()
        if value is not None and freshness.get(key, 1.0) > 0.0
    }

    effective_nominal = {
        key: K.ACI_WEIGHTS[key] * freshness.get(key, 1.0)
        for key in avail
    }
    used_w = sum(effective_nominal.values())

    if used_w <= 0:
        # Sensor reliability is normally always supplied. Keep this function
        # safe even if all effective weights become zero.
        avail = {
            "sensor_reliability": (
                values.get("sensor_reliability")
                if values.get("sensor_reliability") is not None
                else 0.0
            )
        }
        effective_nominal = {
            "sensor_reliability": K.ACI_WEIGHTS["sensor_reliability"]
        }
        used_w = sum(effective_nominal.values())

    # Weighted mean over available evidence.
    raw = sum(
        effective_nominal[key] * value
        for key, value in avail.items()
    ) / used_w

    # Coverage is measured against the complete nominal weight total.
    total_nominal_weight = sum(K.ACI_WEIGHTS.values())
    coverage = used_w / total_nominal_weight if total_nominal_weight else 0.0

    # Safeguard 1: a farm with no experience history cannot reach HIGH.
    cold_start = not farm_has_history
    cold_start_capped = (
        cold_start and raw > K.ACI_COLD_START_CAP
    )
    aci = min(raw, K.ACI_COLD_START_CAP) if cold_start else raw

    # Safeguard 2: insufficient freshness-adjusted evidence cannot support HIGH.
    coverage_capped = (
        not cold_start
        and coverage < K.ACI_MIN_COVERAGE_FOR_HIGH
        and aci > K.ACI_LOW_COVERAGE_CAP
    )
    if coverage_capped:
        aci = K.ACI_LOW_COVERAGE_CAP

    capped = cold_start_capped or coverage_capped

    # Report each component's value, availability, freshness and normalised
    # effective weight. The weights sum to approximately 1 across available
    # components, even when evidence is missing or stale.
    components = {
        key: {
            "value": (
                None if values[key] is None else round(values[key], 3)
            ),
            "weight": K.ACI_WEIGHTS[key],
            "available": key in avail,
            "freshness": (
                round(freshness.get(key, 1.0), 3)
                if values[key] is not None
                else 0.0
            ),
            "effective_weight": (
                round(effective_nominal[key] / used_w, 3)
                if key in avail
                else 0.0
            ),
        }
        for key in K.ACI_WEIGHTS
    }

    notes = []

    if cold_start:
        notes.append(
            "cold_start: no experiences stored yet, so confidence is capped below HIGH"
        )

    if "vision_reliability" not in avail:
        notes.append("no fresh camera evidence")

    if any(value < 0.999 for value in freshness.values()):
        notes.append(
            "evidence_decay_logic: stale evidence contributes less weight"
        )

    if coverage_capped:
        notes.append(
            "low_evidence_coverage: confidence is capped because "
            "insufficient fresh evidence is available"
        )

    limiting_factor = min(avail, key=avail.get) if avail else None

    return {
        "aci": round(aci, 3),
        "level": aci_level(aci),
        "components": components,
        "evidence_coverage": round(coverage, 3),
        "limiting_factor": limiting_factor,
        "cold_start": cold_start,
        "capped": capped,
        "notes": notes,
    }


def fresh_observation(db: Session, device_id: str):
    """Return the latest camera observation if it is within the allowed age."""
    obs = vision_service.get_latest_observation(db, device_id)

    if obs is None:
        return None

    if utcnow() - obs.captured_at > timedelta(
        minutes=K.ACI_VISION_MAX_AGE_MINUTES
    ):
        return None

    return obs


def aci_for_device(
    db: Session,
    device_id: str,
    include_vision: bool = True,
    report: dict | None = None,
) -> dict | None:
    """Gather evidence from the database and compute ACI.

    Returns None if the device has no sensor readings.

    The camera trigger uses include_vision=False so that the decision to
    request a camera image does not depend on evidence from that camera image.
    """
    report = report or reliability_for_device(db, device_id)

    if report is None:
        return None

    found = find_similar_to_current(
        db,
        device_id,
        K.ACI_SIMILARITY_K,
        K.SIMILARITY_MIN_SCORE,
        report=report,
    )
    sim, excluded = found

    vision_rel = None
    pred_conf = None
    behaviour = None

    obs = (
        fresh_observation(db, device_id)
        if include_vision
        else None
    )

    if obs is not None:
        vision_rel = obs.vision_reliability
        pred_conf = obs.effective_confidence
        behaviour = prediction_consistency(
            vision_service.get_observation_history(
                db,
                device_id,
                limit=K.ACI_BEHAVIOUR_WINDOW * 3,
            )
        )

    now = utcnow()
    latest = get_latest(db, device_id)

    sensor_age = (
        age_hours(latest.device_timestamp, now)
        if latest is not None
        else None
    )
    sensor_freshness = decay_factor(
        sensor_age or 0.0,
        K.EDL_SENSOR_HALF_LIFE_HOURS,
        K.EDL_FRESHNESS_FLOOR,
    )

    vision_age = (
        age_hours(obs.captured_at, now)
        if obs is not None
        else None
    )
    vision_freshness = (
        decay_factor(
            vision_age or 0.0,
            K.EDL_VISION_HALF_LIFE_HOURS,
            K.EDL_FRESHNESS_FLOOR,
        )
        if obs is not None
        else 1.0
    )

    # Load recent experience history for similarity and novelty analysis.
    history_rows = list(
        db.scalars(
            select(Experience)
            .where(Experience.device_id == device_id)
            .order_by(Experience.created_at.desc())
            .limit(K.MAX_EXPERIENCES_SCANNED)
        )
    )

    history_conditions = [
        experience.condition for experience in history_rows
    ]

    latest_condition = {
        field: getattr(latest, field)
        for field in K.SENSOR_FIELDS
        if field not in excluded and getattr(latest, field) is not None
    }

    if history_rows:
        md = mahalanobis_novelty(
            latest_condition,
            history_conditions,
            fields=list(latest_condition),
        )
    else:
        md = {
            "available": False,
            "distance": None,
            "novelty": None,
            "fields_used": [],
            "reference_count": 0,
            "reason": "no_experience_history",
        }

    # Mahalanobis novelty moderates historical similarity when enough
    # complete reference history exists.
    base_history = sim["historical_similarity"]

    if md["available"]:
        history_score = base_history * (1.0 - 0.5 * md["novelty"])
    else:
        history_score = base_history

    latest_exp_age = (
        age_hours(history_rows[0].created_at, now)
        if history_rows
        else None
    )
    history_freshness = (
        decay_factor(
            latest_exp_age or 0.0,
            K.EDL_HISTORY_HALF_LIFE_HOURS,
            K.EDL_FRESHNESS_FLOOR,
        )
        if history_rows
        else 1.0
    )

    freshness = {
        "sensor_reliability": sensor_freshness,
        "historical_similarity": history_freshness,
    }

    if obs is not None:
        freshness["vision_reliability"] = vision_freshness
        freshness["prediction_confidence"] = vision_freshness

    out = compute_aci(
        report["summary"]["overall_sensor_reliability"],
        history_score,
        sim["n_experiences_searched"] > 0,
        vision_rel,
        pred_conf,
        behaviour,
        freshness,
    )

    out.update(
        device_id=device_id,
        as_of=report["as_of"],
        vision_used=obs is not None,
        vision_observation_id=obs.id if obs else None,
        n_experiences=sim["n_experiences_searched"],
        n_similar=sim["n_matches"],
        novel_condition=(
            sim["n_experiences_searched"] >= K.UNEXPLAINED_MIN_EXPERIENCES
            and (
                sim["n_matches"] == 0
                or (
                    md["available"]
                    and md["novelty"] >= K.MAHALANOBIS_NOVELTY_THRESHOLD
                )
            )
        ),
        excluded_fields=excluded,
        mahalanobis=md,
        evidence_decay={
            "sensor_age_hours": (
                round(sensor_age, 3)
                if sensor_age is not None
                else None
            ),
            "sensor_freshness": round(sensor_freshness, 3),
            "vision_age_hours": (
                round(vision_age, 3)
                if vision_age is not None
                else None
            ),
            "vision_freshness": (
                round(vision_freshness, 3)
                if obs is not None
                else None
            ),
            "latest_experience_age_hours": (
                round(latest_exp_age, 3)
                if latest_exp_age is not None
                else None
            ),
            "history_freshness": (
                round(history_freshness, 3)
                if history_rows
                else None
            ),
        },
    )

    return out
