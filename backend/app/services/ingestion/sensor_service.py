from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEFAULT_DEVICE_ID, MAX_FUTURE_SKEW_SECONDS
from app.models.sensor import SensorReading
from app.schemas.sensor_schema import SensorReadingIn, to_utc_naive
from app.utils.constants import SENSOR_FIELDS
from app.utils.validation import check_reading_values


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class IngestionError(ValueError):
    pass


def ingest_reading(db: Session, payload: SensorReadingIn) -> SensorReading:
    now = utcnow()
    ts = to_utc_naive(payload.timestamp) if payload.timestamp else now
    if ts > now + timedelta(seconds=MAX_FUTURE_SKEW_SECONDS):
        raise IngestionError("timestamp is in the future")

    missing, flags = check_reading_values({f: getattr(payload, f) for f in SENSOR_FIELDS})

    row = SensorReading(
        device_id=payload.device_id or DEFAULT_DEVICE_ID,
        **{f: getattr(payload, f) for f in SENSOR_FIELDS},
        device_timestamp=ts, received_at=now,
        missing_fields=missing, range_flags=flags,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_latest(db: Session, device_id: str) -> SensorReading | None:
    return db.scalars(
        select(SensorReading).where(SensorReading.device_id == device_id)
        .order_by(SensorReading.device_timestamp.desc(), SensorReading.id.desc())
        .limit(1)
    ).first()


def get_history(db: Session, device_id: str, limit: int = 100,
                start: datetime | None = None, end: datetime | None = None):
    q = select(SensorReading).where(SensorReading.device_id == device_id)
    if start:
        q = q.where(SensorReading.device_timestamp >= to_utc_naive(start))
    if end:
        q = q.where(SensorReading.device_timestamp <= to_utc_naive(end))
    q = q.order_by(SensorReading.device_timestamp.desc(), SensorReading.id.desc()).limit(limit)
    return list(db.scalars(q))
