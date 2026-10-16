
from pydantic import BaseModel, Field, ConfigDict


class ROLAAssessRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    experience_id: int | None = Field(default=None, gt=0)
    predicted_value: float | None = None
    predicted_unit: str | None = None
    predicted_at: str | None = None

    observed_value: float | None = None
    observed_unit: str | None = None
    observed_at: str | None = None

    source_type: str
    value_kind: str = "numeric_measurement"

    independent_of_target_sensor: bool = False
    predicted_depth_cm: float | None = None
    observed_depth_cm: float | None = None

    event_recorded: bool = True
    event_timing_trustworthy: bool = True
    model_calibrated_for_context: bool = False
    observation_quality_ok: bool = True

    max_observation_age_hours: float = Field(
        default=72.0, ge=0
    )


class ROLAAssessResponse(BaseModel):
    comparable: bool
    signed_error: float | None
    absolute_error: float | None
    source_type: str
    independent_verification: bool
    attribution_eligible: bool
    attribution: str
    reasons: list[str]
    recalibration_applied: bool
    recommendation_or_aci_modified: bool


class ROLASummaryRequest(BaseModel):
    errors: list[float | None]


class ROLASummaryResponse(BaseModel):
    count: int
    mean_absolute_error: float | None
    max_absolute_error: float | None
