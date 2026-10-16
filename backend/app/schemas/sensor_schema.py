from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.utils.constants import SENSOR_FIELDS


class SensorReadingIn(BaseModel):
    """Payload from ESP32. Every sensor is optional: a missing value is
    information (Phase 3), not a reason to drop the whole reading."""
    model_config = ConfigDict(extra="ignore")

    device_id: str | None = Field(default=None, max_length=64)
    temperature: float | None = Field(default=None, allow_inf_nan=False)
    humidity: float | None = Field(default=None, allow_inf_nan=False)
    soil: float | None = Field(default=None, allow_inf_nan=False)
    rain: float | None = Field(default=None, allow_inf_nan=False)
    water: float | None = Field(default=None, allow_inf_nan=False)
    light: float | None = Field(default=None, allow_inf_nan=False)
    timestamp: datetime | None = None

    @model_validator(mode="after")
    def _need_at_least_one_sensor(self):
        if all(getattr(self, f) is None for f in SENSOR_FIELDS):
            raise ValueError("payload contains no sensor values")
        return self


class SensorReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    temperature: float | None
    humidity: float | None
    soil: float | None
    rain: float | None
    water: float | None
    light: float | None
    device_timestamp: datetime
    received_at: datetime
    missing_fields: list[str]
    range_flags: list[str]


def to_utc_naive(dt: datetime) -> datetime:
    """Naive input is assumed UTC. Returns naive UTC (what SQLite stores)."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


class EnvironmentalStateOut(BaseModel):
    device_id: str
    as_of: datetime
    soil_state: str
    rain_state: str
    temperature_state: str
    humidity_state: str
    water_state: str
    light_state: str
    water_constraint: bool
    unreliable_inputs: list[str]
