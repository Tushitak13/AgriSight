from datetime import datetime
from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database.database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil: Mapped[float | None] = mapped_column(Float, nullable=True)
    rain: Mapped[float | None] = mapped_column(Float, nullable=True)
    water: Mapped[float | None] = mapped_column(Float, nullable=True)
    light: Mapped[float | None] = mapped_column(Float, nullable=True)
    # when the sensor measured it (UTC) vs when the server got it (UTC)
    device_timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime)
    # ingestion-time findings, consumed later by the Phase 3 reliability engine
    missing_fields: Mapped[list] = mapped_column(JSON, default=list)
    range_flags: Mapped[list] = mapped_column(JSON, default=list)
