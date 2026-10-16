from datetime import datetime
from pydantic import BaseModel


class ACIComponent(BaseModel):
    value: float | None                 # null = component not available
    weight: float                       # nominal weight
    effective_weight: float             # weight actually used after skipping unavailable components
    available: bool
    freshness: float = 1.0


class ACIResult(BaseModel):
    device_id: str
    as_of: datetime
    aci: float                          # 0..1
    level: str                          # HIGH | MEDIUM | LOW
    components: dict[str, ACIComponent]
    evidence_coverage: float            # share of nominal weight that was available
    limiting_factor: str                # lowest-scoring available component
    cold_start: bool                    # farm has no experiences yet
    capped: bool                        # cold-start cap actually lowered the score
    novel_condition: bool               # farm has history but nothing similar to now
    vision_used: bool
    vision_observation_id: int | None
    n_experiences: int
    n_similar: int
    excluded_fields: list[str]
    notes: list[str]
    mahalanobis: dict = {}
    evidence_decay: dict = {}


class CRIComponent(BaseModel):
    value: float
    weight: float


class CRIResult(BaseModel):
    device_id: str
    as_of: datetime
    cri: float                          # 0..1
    cri_percent: float                  # same index on a 0..100 scale for display
    level: str                          # HIGH | MODERATE | LOW
    components: dict[str, CRIComponent]
    weakest_component: str
    stress_severity: float              # 0 none .. 1 severe (stress_tolerance = 1 - this)
    data_support: dict[str, bool]       # false = that recovery component used the neutral prior
    vision_used: bool
    substituted_fields: list[str]       # distrusted sensors replaced by their last known good value
    excluded_fields: list[str]          # distrusted sensors with no valid history, left out entirely
    n_similar_with_outcome: int
