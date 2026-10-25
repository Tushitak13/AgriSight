
"""Vision service: validate upload -> quality -> model -> reliability -> store.

The classifier is replaceable through the VisionModel interface and set_model().
"""

import io
import logging
import uuid
from typing import Protocol

from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models.vision import VisionObservation
from app.services.ingestion.sensor_service import utcnow
from app.services.reliability.vision_reliability import (
    compute_vision_reliability,
)
from app.services.vision.image_quality import assess_image_quality
from app.services.vision.tomato_disease_model import TomatoDiseaseModel
from app.utils import constants as K

logger = logging.getLogger(__name__)

ALLOWED_FORMATS = {
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp",
}


class VisionError(ValueError):
    """Raised when an uploaded image cannot be processed."""


class VisionModel(Protocol):
    name: str

    def predict(self, img: Image.Image) -> dict:
        """Return visual_state, prediction, and confidence."""


class HeuristicVegetationModel:
    """Legacy placeholder model; not a disease classifier."""

    name = "placeholder_color_heuristic"

    def predict(self, img: Image.Image) -> dict:
        import numpy as np

        small = img.convert("RGB")
        small.thumbnail((256, 256))
        hsv = np.asarray(small.convert("HSV"), dtype=np.float32)
        h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]

        leafy = (s > 80) & (v > 50)
        healthy = float((leafy & (h >= 43) & (h < 100)).mean())
        stressed = float((leafy & (h >= 8) & (h < 43)).mean())
        total = healthy + stressed

        if total < 0.02:
            return {
                "visual_state": "no_vegetation_detected",
                "prediction": "unknown",
                "confidence": 0.3,
            }

        ratio = stressed / total

        if ratio > 0.35:
            return {
                "visual_state": "possible_stress",
                "prediction": "stressed",
                "confidence": round(min(0.95, 0.5 + ratio), 3),
            }

        return {
            "visual_state": "healthy_appearance",
            "prediction": "healthy",
            "confidence": round(min(0.95, 0.6 + (0.35 - ratio)), 3),
        }


# Use the trained classifier by default.
# The model is loaded lazily by TomatoDiseaseModel when first needed.
_model: VisionModel = HeuristicVegetationModel()


def get_model() -> VisionModel:
    """Return the currently configured vision model."""
    return _model


def set_model(model: VisionModel) -> None:
    """Replace the model, useful for testing or alternate classifiers."""
    global _model
    _model = model


def analyze_upload(
    db: Session,
    device_id: str,
    raw: bytes,
) -> VisionObservation:
    """Validate, analyze, and persist an uploaded image."""

    if len(raw) > K.MAX_IMAGE_BYTES:
        raise VisionError("image too large (max 8 MB)")

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:
        raise VisionError("file is not a valid image") from exc

    ext = ALLOWED_FORMATS.get((img.format or "").upper())
    if ext is None:
        raise VisionError(
            "unsupported image format (use JPEG, PNG or WEBP)"
        )

    # Correct orientation from phone-camera EXIF metadata.
    img = ImageOps.exif_transpose(img).convert("RGB")

    # Keep the existing image-quality and reliability pipeline.
    quality = assess_image_quality(img)
    model = get_model()

    try:
        pred = model.predict(img)
    except Exception as exc:
        logger.exception("Vision model prediction failed")
        raise VisionError("image inference failed") from exc

    if not isinstance(pred, dict):
        raise VisionError("vision model returned an invalid result")

    visual_state = pred.get("visual_state", "unknown")
    prediction = pred.get("prediction", "unknown")
    confidence = pred.get("confidence")

    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError) as exc:
            raise VisionError(
                "vision model returned invalid confidence"
            ) from exc

        if not 0.0 <= confidence <= 1.0:
            raise VisionError(
                "vision model confidence must be between 0 and 1"
            )

    # Preserve the existing reliability computation.
    rel = compute_vision_reliability(quality, confidence)

    config.VISION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = config.VISION_UPLOAD_DIR / f"{uuid.uuid4().hex}.{ext}"
    path.write_bytes(raw)

    row = VisionObservation(
        device_id=device_id,
        captured_at=utcnow(),
        image_path=str(path),
        quality=quality,
        image_quality=quality["overall"],
        model_name=model.name,
        visual_state=visual_state,
        prediction=prediction,
        model_confidence=confidence,
        vision_reliability=rel["vision_reliability"],
        effective_confidence=rel["effective_confidence"],
        trusted=rel["trusted"],
    )

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_latest_observation(db: Session, device_id: str):
    """Return the latest vision observation for a device."""
    return db.scalars(
        select(VisionObservation)
        .where(VisionObservation.device_id == device_id)
        .order_by(
            VisionObservation.captured_at.desc(),
            VisionObservation.id.desc(),
        )
        .limit(1)
    ).first()


def get_observation_history(
    db: Session,
    device_id: str,
    limit: int = 50,
):
    """Return recent vision observations for a device."""
    return list(
        db.scalars(
            select(VisionObservation)
            .where(VisionObservation.device_id == device_id)
            .order_by(
                VisionObservation.captured_at.desc(),
                VisionObservation.id.desc(),
            )
            .limit(limit)
        )
    )
