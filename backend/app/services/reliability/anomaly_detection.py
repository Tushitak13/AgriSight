"""Anomaly detection primitives: robust statistics (median/MAD), spike score, flatline check.
Median/MAD resist the very outliers we want to detect; mean/std would be dragged by them."""
from statistics import median

from app.utils.constants import SPIKE_Z_THRESHOLD, SPIKE_Z_ZERO

MAD_TO_SIGMA = 1.4826  # makes MAD comparable to std for normal data


def mad(values: list[float]) -> float:
    m = median(values)
    return median(abs(v - m) for v in values)


def robust_z(x: float, history: list[float], scale_floor: float) -> float:
    """|x - median| / robust sigma. scale_floor stops a perfectly flat history
    (MAD = 0) from turning tiny wiggles into huge z-scores."""
    scale = max(MAD_TO_SIGMA * mad(history), scale_floor)
    return abs(x - median(history)) / scale


def population_std(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mu = sum(values) / n
    return (sum((v - mu) ** 2 for v in values) / n) ** 0.5


def spike_score(z: float) -> float:
    """1.0 up to the threshold, linearly falling to 0.0 at SPIKE_Z_ZERO."""
    if z <= SPIKE_Z_THRESHOLD:
        return 1.0
    return max(0.0, 1 - (z - SPIKE_Z_THRESHOLD) / (SPIKE_Z_ZERO - SPIKE_Z_THRESHOLD))


def is_flatline(history: list[float], latest: float, min_points: int) -> bool:
    """Stuck sensor: identical value for the whole history and still identical now."""
    return (len(history) >= min_points and max(history) - min(history) < 1e-9
            and abs(latest - history[-1]) < 1e-9)
