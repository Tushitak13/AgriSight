
"""MobileNetV2 plant disease classifier adapter for AgriSight."""

from __future__ import annotations

import logging
import os
import time
from functools import lru_cache

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

logger = logging.getLogger(__name__)

MODEL_ID = "neghani/plantvillage-mobilenetv2"
MODEL_REVISION = "v1.0"


def _read_confidence_threshold() -> float:
    """Read a provisional threshold, validating that it is between 0 and 1."""
    raw = os.getenv("AGRISIGHT_TOMATO_MIN_CONFIDENCE", "0.60")

    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            "AGRISIGHT_TOMATO_MIN_CONFIDENCE must be a number between 0 and 1"
        ) from exc

    if not 0.0 <= value <= 1.0:
        raise ValueError(
            "AGRISIGHT_TOMATO_MIN_CONFIDENCE must be between 0 and 1"
        )

    return value


# Provisional only; validate on an independent dataset before production.
MIN_CONFIDENCE = _read_confidence_threshold()


@lru_cache(maxsize=1)
def _load_model():
    """Load the model and image processor once per process."""
    processor = AutoImageProcessor.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION
    )
    model = AutoModelForImageClassification.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION
    )
    model.to("cpu")
    model.eval()

    return processor, model


class TomatoDiseaseModel:
    """Implements AgriSight's VisionModel.predict interface."""

    name = f"mobilenetv2_plantvillage_{MODEL_REVISION}"

    def predict(self, img: Image.Image) -> dict:
        """Predict plant disease labels and return uncalibrated softmax scores.

        `confidence` is the top overall class's raw softmax score.
        `probabilities` maps all model labels to their raw softmax scores.
        Neither represents a calibrated probability of correctness.
        """
        start = time.perf_counter()
        model_version = f"{MODEL_ID}@{MODEL_REVISION}"

        try:
            processor, model = _load_model()
            inputs = processor(images=img.convert("RGB"), return_tensors="pt")

            with torch.inference_mode():
                logits = model(**inputs).logits
                scores = torch.softmax(logits, dim=-1)[0]

            labels = model.config.id2label
            probabilities = {
                labels[i]: float(scores[i].item())
                for i in range(len(labels))
            }

            best_id = int(torch.argmax(scores).item())
            best_label = labels[best_id]
            confidence = probabilities[best_label]

            tomato_scores = {
                label: score
                for label, score in probabilities.items()
                if label.startswith("Tomato___")
            }

            best_tomato_class = (
                max(tomato_scores, key=tomato_scores.get)
                if tomato_scores
                else None
            )
            best_tomato_score = (
                tomato_scores[best_tomato_class]
                if best_tomato_class is not None
                else None
            )

            top_predictions = [
                {"class": label, "score": score}
                for label, score in sorted(
                    probabilities.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[:5]
            ]

            if not best_label.startswith("Tomato___"):
                status = "uncertain"
                reason = "non_tomato_top_prediction"
                predicted_class = None
                visual_state = "uncertain_crop"
                prediction = "unknown"

            elif confidence < MIN_CONFIDENCE:
                status = "uncertain"
                reason = "low_confidence"
                predicted_class = None
                visual_state = "uncertain_disease"
                prediction = "unknown"

            else:
                status = "success"
                reason = None
                predicted_class = best_label
                visual_state = (
                    "healthy_appearance"
                    if best_label == "Tomato___healthy"
                    else "possible_disease"
                )
                prediction = best_label.removeprefix("Tomato___")

            return {
                # Existing adapter fields retained for compatibility.
                "visual_state": visual_state,
                "prediction": prediction,
                "confidence": confidence,
                "predicted_class": predicted_class,
                "best_tomato_class": best_tomato_class,
                "best_tomato_score": best_tomato_score,
                "top_predictions": top_predictions,

                # Public inference contract fields.
                "status": status,
                "model_version": model_version,
                "inference_time_ms": round(
                    (time.perf_counter() - start) * 1000, 2
                ),
                "probabilities": probabilities,
                "reason": reason,
            }

        except Exception:
            logger.exception("Tomato disease inference failed")

            return {
                "visual_state": "inference_error",
                "prediction": "unknown",
                "confidence": None,
                "predicted_class": None,
                "best_tomato_class": None,
                "best_tomato_score": None,
                "top_predictions": [],
                "status": "error",
                "model_version": model_version,
                "inference_time_ms": round(
                    (time.perf_counter() - start) * 1000, 2
                ),
                "probabilities": {},
                "reason": "model_error",
            }
