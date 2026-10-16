"""Vision Reliability: a confident prediction on a bad image is NOT trustworthy evidence.
effective_confidence = model_confidence x image reliability."""
from app.utils import constants as K


def compute_vision_reliability(quality: dict, model_confidence: float | None) -> dict:
    rel = quality["overall"]
    effective = None if model_confidence is None else round(model_confidence * rel, 3)
    return dict(
        vision_reliability=round(rel, 3),
        effective_confidence=effective,
        trusted=rel >= K.VISION_RELIABILITY_MIN,
        issues=list(quality["issues"]),
    )
