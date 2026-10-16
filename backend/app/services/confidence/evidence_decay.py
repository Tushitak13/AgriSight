"""Evidence Decay Logic (EDL): exponential freshness weighting for time-sensitive evidence.

Decay is deliberately applied to evidence weight, not by rewriting the measured value.
A half-life of H means evidence contributes half its nominal weight after H time units.
"""
from datetime import datetime, timezone
import math


def decay_factor(age_hours: float, half_life_hours: float, floor: float = 0.0) -> float:
    """Return a clamped exponential freshness factor in [floor, 1]."""
    if half_life_hours <= 0:
        raise ValueError("half_life_hours must be positive")
    age = max(0.0, float(age_hours))
    floor = max(0.0, min(1.0, float(floor)))
    return max(floor, min(1.0, math.exp(-math.log(2.0) * age / half_life_hours)))


def age_hours(timestamp: datetime | None, now: datetime) -> float | None:
    """Age in hours, normalising aware timestamps to naive UTC when needed."""
    if timestamp is None:
        return None
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    if now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)
    return max(0.0, (now - timestamp).total_seconds() / 3600.0)
