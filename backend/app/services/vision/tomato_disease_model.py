
"""MobileNetV2 tomato disease classifier adapter for AgriSight."""

from __future__ import annotations

import logging
import time
from functools import lru_cache

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

logger = logging.getLogger(__name__)

MODEL_ID = "neghani/plantvillage-mobilenetv2"
MODEL_REVISION = "v1.0"

# Provisional smoke-test threshold only; validate before production.
MIN_CONFIDENCE = 0.60


@lru_cache(maxsize=1)
def _load_model():
    """Load the model once per process and reuse it for subsequent images."""
    processor = AutoImageProcessor.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
    )
    model = AutoModelForImageClassification.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
    )
    model.to("cpu")
    model.eval()
    return processor, model


class TomatoDiseaseModel:
    """Implements the existing AgriSight VisionModel.predict interface."""

    name = f"mobilenetv2_plantvillage_{MODEL_REVISION}"

    def predict(self, img: Image.Image) -> dict:
        start = time.perf_counter()

        try:
            processor, model = _load_model()
            rgb_image = img.convert("RGB")
            inputs = processor(images=rgb_image, return_tensors="pt")

            with torch.inference_mode():
                logits = model(**inputs).logits
                probabilities = torch.softmax(logits, dim=-1)[0]

            labels = model.config.id2label
            best_id = int(torch.argmax(probabilities).item())
            best_label = labels[best_id]
            confidence = float(probabilities[best_id].item())

            tomato_scores = [
                (labels[i], float(probabilities[i].item()))
                for i in range(len(labels))
                if labels[i].startswith("Tomato___")
            ]
            best_tomato = max(
                tomato_scores,
                key=lambda item: item[1],
                default=(None, 0.0),
            )

            top_predictions = sorted(
                [
                    {
                        "class": labels[i],
                        "score": float(probabilities[i].item()),
                    }
                    for i in range(len(labels))
                ],
                key=lambda item: item["score"],
                reverse=True,
            )[:5]

            if not best_label.startswith("Tomato___"):
                status = "uncertain"
                visual_state = "uncertain_crop"
                prediction = "unknown"
            elif confidence < MIN_CONFIDENCE:
                status = "uncertain"
                visual_state = "uncertain_disease"
                prediction = "unknown"
            else:
                status = "model_prediction"
                visual_state = (
                    "healthy_appearance"
                    if best_label == "Tomato___healthy"
                    else "possible_disease"
                )
                prediction = best_label.removeprefix("Tomato___")

            return {
                "visual_state": visual_state,
                "prediction": prediction,
                "confidence": confidence,
                "predicted_class": best_label,
                "best_tomato_class": best_tomato[0],
                "best_tomato_score": best_tomato[1],
                "top_predictions": top_predictions,
                "status": status,
                "model_version": f"{MODEL_ID}@{MODEL_REVISION}",
                "inference_time_ms": round(
                    (time.perf_counter() - start) * 1000, 2
                ),
            }

        except Exception:
            logger.exception("Tomato disease inference failed")
            # Preserve the service contract instead of inventing a prediction.
            return {
                "visual_state": "inference_error",
                "prediction": "unknown",
                "confidence": None,
                "predicted_class": None,
                "best_tomato_class": None,
                "best_tomato_score": None,
                "top_predictions": [],
                "status": "error",
                "model_version": f"{MODEL_ID}@{MODEL_REVISION}",
                "inference_time_ms": round(
                    (time.perf_counter() - start) * 1000, 2
                ),
            }
