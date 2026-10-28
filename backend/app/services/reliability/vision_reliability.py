
"""Vision reliability combines image quality with model confidence."""

from app.utils import constants as K

# Initial confidence threshold; validate and tune using held-out images.
VISION_MODEL_CONFIDENCE_MIN = 0.50


def compute_vision_reliability(
    quality: dict,
    model_confidence: float | None,
) -> dict:
    image_reliability = quality["overall"]

    effective = (
        None
        if model_confidence is None
        else round(model_confidence * image_reliability, 3)
    )

    trusted = (
        image_reliability >= K.VISION_RELIABILITY_MIN
        and effective is not None
        and effective >= VISION_MODEL_CONFIDENCE_MIN
    )

    issues = list(quality["issues"])

    if effective is None:
        issues.append("model_confidence_unavailable")
    elif effective < VISION_MODEL_CONFIDENCE_MIN:
        issues.append("low_model_confidence")

    return {
        "vision_reliability": round(image_reliability, 3),
        "effective_confidence": effective,
        "trusted": trusted,
        "issues": issues,
    }
