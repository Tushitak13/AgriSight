import math
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.utils import constants as K

OutcomeStatus = Literal["SUCCESSFUL", "PARTIALLY_SUCCESSFUL", "UNSUCCESSFUL"]
NAME_PATTERN = r"^[a-z0-9_]+$"


class Condition(BaseModel):
    """A snapshot of the six sensor values. Every field optional, at least one required.
    Unlike live ingestion, stored experiences must be physically plausible (in nominal range)."""
    model_config = ConfigDict(extra="ignore")

    temperature: float | None = Field(default=None, allow_inf_nan=False)
    humidity: float | None = Field(default=None, allow_inf_nan=False)
    soil: float | None = Field(default=None, allow_inf_nan=False)
    rain: float | None = Field(default=None, allow_inf_nan=False)
    water: float | None = Field(default=None, allow_inf_nan=False)
    light: float | None = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def _check(self):
        if all(getattr(self, f) is None for f in K.SENSOR_FIELDS):
            raise ValueError("condition contains no sensor values")
        for f in K.SENSOR_FIELDS:
            v = getattr(self, f)
            if v is None:
                continue
            lo, hi = K.NOMINAL_RANGES[f]
            if not math.isfinite(v) or v < lo or v > hi:
                raise ValueError(f"{f}={v} is outside the plausible range {lo}..{hi}")
        return self

    def as_dict(self) -> dict:
        return {f: getattr(self, f) for f in K.SENSOR_FIELDS if getattr(self, f) is not None}


class OutcomeIn(BaseModel):
    status: OutcomeStatus
    after: Condition | None = None      # readings observed after the intervention


class ExperienceCreate(BaseModel):
    device_id: str | None = Field(default=None, max_length=64)
    condition: Condition
    decision: str | None = Field(default=None, max_length=64, pattern=NAME_PATTERN)
    intervention: str = Field(min_length=1, max_length=64, pattern=NAME_PATTERN)
    expected_soil_change: float | None = Field(default=None, ge=-100, le=100, allow_inf_nan=False)
    source: Literal["real", "seed"] = "real"
    outcome: OutcomeIn | None = None    # omit => PENDING


class ExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    created_at: datetime
    source: str
    condition: dict
    condition_states: dict
    decision: str | None
    intervention: str
    expected_soil_change: float | None
    outcome_status: str | None          # null = pending
    outcome_condition: dict | None
    soil_change: float | None
    outcome_recorded_at: datetime | None


# ---- similarity
class SimilaritySearchIn(BaseModel):
    device_id: str | None = Field(default=None, max_length=64)
    condition: Condition
    k: int = Field(default=K.SIMILARITY_DEFAULT_K, ge=1, le=50)
    min_similarity: float = Field(default=K.SIMILARITY_MIN_SCORE, ge=0, le=1)
    only_with_outcome: bool = False


class SimilarMatch(BaseModel):
    similarity: float
    distance: float
    coverage: float                     # share of total weight that could be compared
    fields_compared: list[str]
    field_distances: dict[str, float]
    experience: ExperienceOut


class InterventionStat(BaseModel):
    intervention: str
    n: int                              # similar experiences with a recorded outcome
    weighted_success: float             # similarity-weighted outcome score, 0..1
    mean_similarity: float
    mean_soil_change: float | None


class SimilarityResult(BaseModel):
    device_id: str
    query: dict
    excluded_fields: list[str]          # dropped from the query because their sensor was unreliable
    n_experiences_searched: int
    n_matches: int
    has_history: bool
    historical_similarity: float        # 0..1, feeds ACI in Phase 6
    matches: list[SimilarMatch]
    intervention_summary: list[InterventionStat]
