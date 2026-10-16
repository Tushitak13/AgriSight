"""CRI - Crop Resilience Index (Module 10). A project-specific index, NOT an established
agronomic metric: it estimates how well the crop can tolerate stress and recover from it.

    CRI = 0.30 environmental_stability + 0.30 stress_tolerance
        + 0.20 historical_recovery     + 0.20 recent_response          (all 0..1)

environmental_stability  average favourability of the last N readings (steady good conditions = high)
stress_tolerance         1 - stress severity. Severity is dominated by the single worst factor
                         (0.7 worst + 0.3 average) and is raised by trusted visual stress evidence
historical_recovery      similarity-weighted outcome score of similar past experiences
recent_response          recency-weighted outcome score of the latest interventions

Recovery components have no data on a new farm. They then take the neutral prior 0.5
(not 0, not 1) and are flagged in `data_support`, so CRI never claims a recovery record it lacks.
A sensor the reliability engine distrusts is NOT simply ignored (that would hide its bad news and make
the crop look healthier): its latest value is replaced by the median of its recent valid readings
("last known good"). Only if it has no valid history is it excluded."""
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.experience import Experience
from app.services.confidence.aci import fresh_observation
from app.services.ingestion import sensor_service
from app.services.reliability.sensor_reliability import reliability_for_device
from app.services.similarity.retrieval import find_similar
from app.services.state.environmental_state import classify
from app.utils import constants as K


def cri_level(cri: float) -> str:
    return "HIGH" if cri >= K.CRI_HIGH else "LOW" if cri < K.CRI_LOW else "MODERATE"


def field_favourability(field: str, value: float | None) -> float | None:
    if value is None:
        return None
    return K.STATE_FAVOURABILITY[field].get(classify(field, value))


def reading_favourability(values: dict, exclude: set | frozenset = frozenset()) -> float | None:
    """Weighted mean favourability over the usable fields of ONE reading (None if none usable)."""
    num = den = 0.0
    for f in K.SENSOR_FIELDS:
        fav = None if f in exclude else field_favourability(f, values.get(f))
        if fav is None:
            continue
        num += K.CRI_FIELD_WEIGHTS[f] * fav
        den += K.CRI_FIELD_WEIGHTS[f]
    return num / den if den else None


def stress_severity(values: dict, exclude: set | frozenset = frozenset(),
                    vision_state: str | None = None, vision_reliability: float = 0.0) -> float | None:
    """0 (no stress) .. 1 (severe). Sensor severity is 0.7 x worst factor + 0.3 x average factor;
    trusted visual stress can raise it (scaled by image reliability) but never lowers it."""
    distress = []
    for f in K.SENSOR_FIELDS:
        fav = None if f in exclude else field_favourability(f, values.get(f))
        if fav is not None:
            distress.append(1.0 - fav)
    sensor_sev = None
    if distress:
        m = K.CRI_SEVERITY_MAX_SHARE
        sensor_sev = m * max(distress) + (1 - m) * (sum(distress) / len(distress))
    vis = K.VISION_STRESS_SEVERITY.get(vision_state) if vision_state else None
    vis_sev = None if vis is None else vis * vision_reliability
    if sensor_sev is None and vis_sev is None:
        return None
    return max(x for x in (sensor_sev, vis_sev) if x is not None)


def recent_response_score(outcome_statuses_newest_first: list[str]) -> float | None:
    """Recency-weighted mean outcome score (newest weight 1, each older one x CRI_RECENCY_DECAY)."""
    statuses = outcome_statuses_newest_first[:K.CRI_RECENT_OUTCOMES]
    if not statuses:
        return None
    weights = [K.CRI_RECENCY_DECAY ** i for i in range(len(statuses))]
    return sum(w * K.OUTCOME_SCORES[s] for w, s in zip(weights, statuses)) / sum(weights)


def compute_cri(environmental_stability: float, severity: float,
                historical_recovery: float | None, recent_response: float | None) -> dict:
    """Pure fusion. severity 0..1 (higher = worse). None recovery inputs take the neutral prior."""
    clamp = lambda x: max(0.0, min(1.0, float(x)))
    comps = dict(environmental_stability=clamp(environmental_stability),
                 stress_tolerance=clamp(1.0 - severity),
                 historical_recovery=clamp(K.CRI_NEUTRAL if historical_recovery is None else historical_recovery),
                 recent_response=clamp(K.CRI_NEUTRAL if recent_response is None else recent_response))
    cri = sum(K.CRI_WEIGHTS[k] * v for k, v in comps.items())
    return dict(cri=round(cri, 3), cri_percent=round(cri * 100, 1), level=cri_level(cri),
                components={k: dict(value=round(v, 3), weight=K.CRI_WEIGHTS[k]) for k, v in comps.items()},
                weakest_component=min(comps, key=comps.get),
                data_support=dict(historical_recovery=historical_recovery is not None,
                                  recent_response=recent_response is not None))


def _recent_outcomes(db: Session, device_id: str) -> list[str]:
    rows = db.scalars(select(Experience).where(Experience.device_id == device_id,
                                               Experience.outcome_status.is_not(None))
                      .order_by(Experience.outcome_recorded_at.desc(), Experience.id.desc())
                      .limit(K.CRI_RECENT_OUTCOMES))
    return [r.outcome_status for r in rows]


def cri_for_device(db: Session, device_id: str) -> dict | None:
    """Gather inputs from the database and compute CRI. None if the device has no readings."""
    report = reliability_for_device(db, device_id)
    if report is None:
        return None
    rows = sensor_service.get_history(db, device_id, limit=K.CRI_WINDOW)      # newest first
    readings = [{f: getattr(r, f) for f in K.SENSOR_FIELDS} for r in rows]
    substituted, excluded = [], []
    for f in sorted(report["anomalous_sensors"]):                  # low score OR spike OR out of range
        lo, hi = K.NOMINAL_RANGES[f]
        prior = [r[f] for r in readings[1:] if r[f] is not None and lo <= r[f] <= hi]
        if prior:
            readings[0][f] = median(prior)
            substituted.append(f)
        else:
            excluded.append(f)
    exclude = set(excluded)

    per_reading = [x for x in (reading_favourability(v, exclude) for v in readings) if x is not None]
    stability = sum(per_reading) / len(per_reading) if per_reading else K.CRI_NEUTRAL
    latest = readings[0]
    obs = fresh_observation(db, device_id)
    vision_used = obs is not None and obs.trusted and obs.visual_state in K.VISION_STRESS_SEVERITY
    severity = stress_severity(latest, exclude,
                               obs.visual_state if vision_used else None,
                               obs.vision_reliability if vision_used else 0.0)
    if severity is None:
        severity = 1.0 - K.CRI_NEUTRAL

    # search with the same repaired condition CRI itself uses (last-known-good for distrusted sensors)
    sim = find_similar(db, device_id, {f: v for f, v in latest.items() if f not in exclude},
                       10, K.SIMILARITY_MIN_SCORE)
    scored = [(c["similarity"], K.OUTCOME_SCORES[e.outcome_status])
              for e, c in sim["matches"] if e.outcome_status is not None]
    historical = (sum(s * o for s, o in scored) / sum(s for s, _ in scored)
                  if scored and sum(s for s, _ in scored) > 0 else None)

    out = compute_cri(stability, severity, historical, recent_response_score(_recent_outcomes(db, device_id)))
    out.update(device_id=device_id, as_of=report["as_of"], stress_severity=round(severity, 3),
               vision_used=vision_used, substituted_fields=substituted, excluded_fields=excluded,
               n_similar_with_outcome=len(scored))
    return out
