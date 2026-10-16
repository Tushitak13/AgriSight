"""Vision service: validate upload -> quality -> model -> vision reliability -> store.
The CV model is a plug-in (PPT does not fix one). Swap it with set_model(YourModel())."""
import io
import uuid
from typing import Protocol

from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models.vision import VisionObservation
from app.services.ingestion.sensor_service import utcnow
from app.services.reliability.vision_reliability import compute_vision_reliability
from app.services.vision.image_quality import assess_image_quality
from app.utils import constants as K

ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class VisionError(ValueError):
    pass


class VisionModel(Protocol):
    name: str

    def predict(self, img: Image.Image) -> dict:
        """Return {visual_state: str, prediction: str, confidence: float|None}."""


class HeuristicVegetationModel:
    """PLACEHOLDER, not a disease classifier. Compares green vs yellow/brown leaf pixels
    so the full pipeline can be tested end to end. Replace with a trained model later."""
    name = "placeholder_color_heuristic"

    def predict(self, img: Image.Image) -> dict:
        small = img.convert("RGB")
        small.thumbnail((256, 256))
        import numpy as np
        hsv = np.asarray(small.convert("HSV"), dtype=np.float32)
        h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        leafy = (s > 80) & (v > 50)
        healthy = float((leafy & (h >= 43) & (h < 100)).mean())
        stressed = float((leafy & (h >= 8) & (h < 43)).mean())
        total = healthy + stressed
        if total < 0.02:
            return dict(visual_state="no_vegetation_detected", prediction="unknown", confidence=0.3)
        ratio = stressed / total
        if ratio > 0.35:
            return dict(visual_state="possible_stress", prediction="stressed",
                        confidence=round(min(0.95, 0.5 + ratio), 3))
        return dict(visual_state="healthy_appearance", prediction="healthy",
                    confidence=round(min(0.95, 0.6 + (0.35 - ratio)), 3))


_model: VisionModel = HeuristicVegetationModel()


def get_model() -> VisionModel:
    return _model


def set_model(model: VisionModel) -> None:
    global _model
    _model = model


def analyze_upload(db: Session, device_id: str, raw: bytes) -> VisionObservation:
    if len(raw) > K.MAX_IMAGE_BYTES:
        raise VisionError("image too large (max 8 MB)")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise VisionError("file is not a valid image")
    ext = ALLOWED_FORMATS.get((img.format or "").upper())
    if ext is None:
        raise VisionError("unsupported image format (use JPEG, PNG or WEBP)")
    img = ImageOps.exif_transpose(img)  # phone photos may be rotated via EXIF

    quality = assess_image_quality(img)
    model = get_model()
    pred = model.predict(img)
    rel = compute_vision_reliability(quality, pred.get("confidence"))

    config.VISION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = config.VISION_UPLOAD_DIR / f"{uuid.uuid4().hex}.{ext}"
    path.write_bytes(raw)

    row = VisionObservation(
        device_id=device_id, captured_at=utcnow(), image_path=str(path),
        quality=quality, image_quality=quality["overall"], model_name=model.name,
        visual_state=pred["visual_state"], prediction=pred["prediction"],
        model_confidence=pred.get("confidence"), vision_reliability=rel["vision_reliability"],
        effective_confidence=rel["effective_confidence"], trusted=rel["trusted"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_latest_observation(db: Session, device_id: str):
    return db.scalars(select(VisionObservation).where(VisionObservation.device_id == device_id)
                      .order_by(VisionObservation.captured_at.desc(), VisionObservation.id.desc())
                      .limit(1)).first()


def get_observation_history(db: Session, device_id: str, limit: int = 50):
    return list(db.scalars(select(VisionObservation).where(VisionObservation.device_id == device_id)
                           .order_by(VisionObservation.captured_at.desc(), VisionObservation.id.desc())
                           .limit(limit)))
