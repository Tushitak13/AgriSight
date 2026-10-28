from datetime import datetime
from pydantic import BaseModel, ConfigDict


class VisionObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    device_id: str
    captured_at: datetime
    image_path: str
    quality: dict
    image_quality: float
    model_name: str
    visual_state: str
    prediction: str
    model_confidence: float | None
    vision_reliability: float
    effective_confidence: float | None
    trusted: bool
    detections: list[dict] | None = None


class TriggerDecision(BaseModel):
    trigger: bool
    reasons: list[str]
    overall_sensor_reliability: float | None
    anomalous_sensors: list[str]
    aci: float | None = None
