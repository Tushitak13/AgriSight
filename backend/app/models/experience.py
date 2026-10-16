from datetime import datetime
from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database.database import Base


class Experience(Base):
    """One farm-specific record: condition -> decision -> intervention -> observed outcome.
    A row with outcome_status = NULL is still PENDING (intervention done, result not yet observed)."""
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str] = mapped_column(String(16), default="real", index=True)   # real | seed

    condition: Mapped[dict] = mapped_column(JSON)            # {"soil": 31, "rain": 0, ...} present fields only
    condition_states: Mapped[dict] = mapped_column(JSON)     # {"soil_state": "DRY", ...}
    decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    intervention: Mapped[str] = mapped_column(String(64), index=True)
    expected_soil_change: Mapped[float | None] = mapped_column(Float, nullable=True)  # used by Phase 8 recalibration

    outcome_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    outcome_condition: Mapped[dict | None] = mapped_column(JSON, nullable=True)      # readings after the intervention
    soil_change: Mapped[float | None] = mapped_column(Float, nullable=True)          # actual after - before
    outcome_recorded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
