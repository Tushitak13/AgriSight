
"""Persistent audit records for offline soil-change recalibration."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class RecalibrationAssessment(Base):
    """Auditable ROLA assessment linked to one completed experience."""

    __tablename__ = "recalibration_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    experience_id: Mapped[int] = mapped_column(
        ForeignKey("experiences.id"), unique=True, index=True
    )
    predicted_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    observed_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)

    predicted_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="unknown")
    value_kind: Mapped[str] = mapped_column(String(32), default="numeric_measurement")

    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    predicted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    predicted_depth_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_depth_cm: Mapped[float | None] = mapped_column(Float, nullable=True)

    independent_of_target_sensor: Mapped[bool] = mapped_column(Boolean)
    event_recorded: Mapped[bool] = mapped_column(Boolean)
    event_timing_trustworthy: Mapped[bool] = mapped_column(Boolean)
    model_calibrated_for_context: Mapped[bool] = mapped_column(Boolean)
    observation_quality_ok: Mapped[bool] = mapped_column(Boolean)

    comparable: Mapped[bool] = mapped_column(Boolean)
    attribution_eligible: Mapped[bool] = mapped_column(Boolean, index=True)
    signed_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    absolute_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasons: Mapped[list] = mapped_column(JSON)

    assessed_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class RecalibrationCandidate(Base):
    """Offline candidate and holdout metrics; never activates a model."""

    __tablename__ = "recalibration_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    method: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(64))

    training_samples: Mapped[int] = mapped_column(Integer)
    correction: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_mae_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_mae_after: Mapped[float | None] = mapped_column(Float, nullable=True)

    holdout_samples: Mapped[int] = mapped_column(Integer, default=0)
    baseline_mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidate_mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_improvement: Mapped[float | None] = mapped_column(Float, nullable=True)

    training_experience_ids: Mapped[list] = mapped_column(JSON)
    holdout_experience_ids: Mapped[list] = mapped_column(JSON)

    deployment_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    active_model_modified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
