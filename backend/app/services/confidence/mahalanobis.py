"""Multivariate novelty detection for environmental sensor conditions.

Uses robustly bounded, domain-scaled sensor features and a pseudo-inverse covariance so
correlated sensors and singular covariance matrices are handled safely. It is a novelty
signal, not a crop-disease classifier. At least five complete historical vectors are needed.
"""
import math
import numpy as np
from app.utils import constants as K

MIN_REFERENCE_ROWS = 5


def _feature(field: str, value: float) -> float:
    # Map unlike units onto comparable scales. Light is log-transformed first.
    if field == "light":
        value = math.log1p(max(0.0, float(value)))
    else:
        value = float(value)
    lo, hi = K.NOMINAL_RANGES[field]
    if field == "light":
        lo, hi = 0.0, math.log1p(hi)
    return (value - lo) / max(hi - lo, 1e-9)


def mahalanobis_novelty(current: dict, historical_conditions: list[dict],
                        fields: list[str] | None = None) -> dict:
    """Return distance, bounded novelty (0 familiar .. 1 novel), and diagnostics.

    Uses only fields present in the current condition and complete in every selected
    reference vector. Fewer than MIN_REFERENCE_ROWS means insufficient evidence.
    """
    fields = fields or [f for f in K.SENSOR_FIELDS if current.get(f) is not None]
    fields = [f for f in fields if current.get(f) is not None and
              all(row.get(f) is not None for row in historical_conditions)]
    if len(fields) < 2 or len(historical_conditions) < MIN_REFERENCE_ROWS:
        return {"available": False, "distance": None, "novelty": None,
                "fields_used": fields, "reference_count": len(historical_conditions),
                "reason": "insufficient_complete_history"}
    x = np.asarray([[_feature(f, row[f]) for f in fields] for row in historical_conditions], dtype=float)
    q = np.asarray([_feature(f, current[f]) for f in fields], dtype=float)
    # Winsorise each feature to reduce impact of bad historical readings.
    lo = np.quantile(x, 0.05, axis=0); hi = np.quantile(x, 0.95, axis=0)
    x = np.clip(x, lo, hi)
    mean = np.mean(x, axis=0)
    cov = np.atleast_2d(np.cov(x, rowvar=False))
    # Small diagonal regularisation stabilises near-constant features.
    cov += np.eye(cov.shape[0]) * 1e-4
    delta = q - mean
    d2 = max(0.0, float(delta @ np.linalg.pinv(cov) @ delta.T))
    distance = math.sqrt(d2)
    # Dimension-adjusted threshold; smooth mapping avoids a brittle binary novelty flag.
    threshold = 2.0 * math.sqrt(len(fields))
    novelty = max(0.0, min(1.0, distance / (distance + threshold)))
    return {"available": True, "distance": round(distance, 4), "novelty": round(novelty, 4),
            "fields_used": fields, "reference_count": len(historical_conditions),
            "threshold": round(threshold, 4), "reason": None}
