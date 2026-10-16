"""Similarity Engine (Module 8). Pure functions, no database.

distance   = sum(w_i * d_i) / sum(w_i)   over the fields BOTH conditions have
similarity = 1 - distance                (1.0 identical, 0.0 completely different)
d_i        = min(1, |a_i - b_i| / scale_i)   (light is compared on a log scale)

Missing fields are skipped and the remaining weights are re-normalised, so a past
experience with a dropped sensor is still comparable. If the shared fields carry too
little weight the pair is not comparable at all (None) rather than guessed at."""
import math
from collections import defaultdict

from app.utils import constants as K

_TOTAL_WEIGHT = sum(K.SIMILARITY_WEIGHTS.values())


def _prep(field: str, value: float) -> float:
    if field in K.SIMILARITY_LOG_FIELDS:
        return math.log1p(max(float(value), 0.0))
    return float(value)


def field_distance(field: str, a: float, b: float) -> float:
    return min(1.0, abs(_prep(field, a) - _prep(field, b)) / K.SIMILARITY_SCALES[field])


def compare(current: dict, past: dict) -> dict | None:
    """Similarity of two {field: value} conditions, or None if not comparable."""
    num = den = 0.0
    dists: dict[str, float] = {}
    for f in K.SENSOR_FIELDS:
        a, b = current.get(f), past.get(f)
        if a is None or b is None:
            continue
        d = field_distance(f, a, b)
        w = K.SIMILARITY_WEIGHTS[f]
        dists[f] = round(d, 4)
        num += w * d
        den += w
    if den < K.SIMILARITY_MIN_COMMON_WEIGHT:
        return None
    distance = num / den
    return dict(similarity=round(1.0 - distance, 4), distance=round(distance, 4),
                coverage=round(den / _TOTAL_WEIGHT, 4), fields_compared=list(dists),
                field_distances=dists)


def rank(current: dict, experiences, k: int, min_similarity: float) -> list[tuple]:
    """Top-k (experience, comparison) pairs with similarity >= min_similarity, best first.
    `experiences` need .id and .condition. Ties go to the newer experience."""
    scored = []
    for exp in experiences:
        cmp = compare(current, exp.condition)
        if cmp is not None and cmp["similarity"] >= min_similarity:
            scored.append((exp, cmp))
    scored.sort(key=lambda p: (-p[1]["similarity"], -p[0].id))
    return scored[:k]


def historical_similarity(matches: list[tuple]) -> float:
    """One 0..1 number for ACI: mean of (similarity x coverage) over the matches, scaled down while
    there are fewer than HISTORY_FULL_CONFIDENCE_MATCHES of them (one close match is weak history).
    Coverage matters: a match that could only compare 70% of the weight (e.g. soil was distrusted
    and left out) is weaker evidence than a full comparison."""
    if not matches:
        return 0.0
    mean = sum(c["similarity"] * c["coverage"] for _, c in matches) / len(matches)
    return round(mean * min(1.0, len(matches) / K.HISTORY_FULL_CONFIDENCE_MATCHES), 4)


def summarize_interventions(matches: list[tuple]) -> list[dict]:
    """Per intervention, how well it worked in similar past situations (only experiences with an
    outcome). Success is similarity-weighted so closer experiences count more. Used by FLAI."""
    groups = defaultdict(list)
    for exp, cmp in matches:
        if exp.outcome_status is not None:
            groups[exp.intervention].append((exp, cmp["similarity"]))
    out = []
    for name, items in groups.items():
        sims = [s for _, s in items]
        wsum = sum(sims)
        score = (sum(s * K.OUTCOME_SCORES[e.outcome_status] for e, s in items) / wsum) if wsum > 0 else 0.0
        changes = [e.soil_change for e, _ in items if e.soil_change is not None]
        out.append(dict(intervention=name, n=len(items), weighted_success=round(score, 4),
                        mean_similarity=round(wsum / len(items), 4),
                        mean_soil_change=round(sum(changes) / len(changes), 2) if changes else None))
    out.sort(key=lambda r: (-r["weighted_success"], -r["n"], r["intervention"]))
    return out
