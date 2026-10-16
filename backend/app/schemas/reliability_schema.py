from datetime import datetime
from pydantic import BaseModel


class SensorReliability(BaseModel):
    score: float
    range_score: float
    spike_score: float
    stability_score: float
    completeness_score: float
    consistency_penalty: float
    flags: list[str]


class ConsistencyFinding(BaseModel):
    rule: str
    sensors: list[str]
    penalty: float
    message: str


class ReliabilityReport(BaseModel):
    device_id: str
    as_of: datetime
    window_size: int
    summary: dict[str, float]            # soil_reliability ... overall_sensor_reliability
    sensors: dict[str, SensorReliability]
    consistency_findings: list[ConsistencyFinding]
    weakest_sensor: str
    anomalous_sensors: list[str]
    anomaly_detected: bool
