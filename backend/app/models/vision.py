from datetime import datetime
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database.database import Base


class VisionObservation(Base):
    __tablename__ = "vision_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    image_path: Mapped[str] = mapped_column(String(512))
    quality: Mapped[dict] = mapped_column(JSON)
    image_quality: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(64))
    visual_state: Mapped[str] = mapped_column(String(64))
    prediction: Mapped[str] = mapped_column(String(64))
    model_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    vision_reliability: Mapped[float] = mapped_column(Float)
    effective_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    trusted: Mapped[bool] = mapped_column(Boolean)

    # Add this line
    detections: Mapped[list | None] = mapped_column(JSON, nullable=True)