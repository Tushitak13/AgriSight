
from types import SimpleNamespace

import torch
from PIL import Image

from app.services.vision import tomato_disease_model as disease_model


LABELS = {
    0: "Tomato___Early_blight",
    1: "Strawberry___Leaf_scorch",
    2: "Tomato___healthy",
}


class FakeProcessor:
    def __call__(self, images, return_tensors):
        return {}


class FakeModel:
    def __init__(self, logits):
        self.config = SimpleNamespace(id2label=LABELS)
        self.logits = torch.tensor([logits], dtype=torch.float32)

    def __call__(self, **inputs):
        return SimpleNamespace(logits=self.logits)


def run_with_logits(monkeypatch, logits):
    monkeypatch.setattr(
        disease_model,
        "_load_model",
        lambda: (FakeProcessor(), FakeModel(logits)),
    )

    return disease_model.TomatoDiseaseModel().predict(
        Image.new("RGB", (32, 32), "green")
    )


def test_confident_tomato_prediction_returns_success(monkeypatch):
    monkeypatch.setattr(disease_model, "MIN_CONFIDENCE", 0.60)

    result = run_with_logits(monkeypatch, [4.0, 0.0, 0.0])

    assert result["status"] == "success"
    assert result["predicted_class"] == "Tomato___Early_blight"
    assert result["reason"] is None
    assert len(result["probabilities"]) == len(LABELS)
    assert 0.0 <= result["confidence"] <= 1.0
    assert abs(sum(result["probabilities"].values()) - 1.0) < 1e-6
    assert result["model_version"] == (
        f"{disease_model.MODEL_ID}@{disease_model.MODEL_REVISION}"
    )
    assert result["inference_time_ms"] >= 0


def test_non_tomato_top_prediction_is_uncertain(monkeypatch):
    monkeypatch.setattr(disease_model, "MIN_CONFIDENCE", 0.60)

    result = run_with_logits(monkeypatch, [0.0, 4.0, 0.0])

    assert result["status"] == "uncertain"
    assert result["predicted_class"] is None
    assert result["prediction"] == "unknown"
    assert result["reason"] == "non_tomato_top_prediction"
    assert result["best_tomato_class"] == "Tomato___Early_blight"
    assert len(result["probabilities"]) == len(LABELS)
    assert abs(sum(result["probabilities"].values()) - 1.0) < 1e-6
    assert result["model_version"] == (
        f"{disease_model.MODEL_ID}@{disease_model.MODEL_REVISION}"
    )
    assert result["inference_time_ms"] >= 0


def test_low_confidence_tomato_prediction_is_uncertain(monkeypatch):
    monkeypatch.setattr(disease_model, "MIN_CONFIDENCE", 0.60)

    # All logits are equal, so the top score is 1/3, below the threshold.
    # The first class wins the tie and is a tomato disease class.
    result = run_with_logits(monkeypatch, [0.0, 0.0, 0.0])

    assert result["status"] == "uncertain"
    assert result["predicted_class"] is None
    assert result["prediction"] == "unknown"
    assert result["reason"] == "low_confidence"
    assert result["best_tomato_class"] == "Tomato___Early_blight"
    assert len(result["probabilities"]) == len(LABELS)
    assert abs(sum(result["probabilities"].values()) - 1.0) < 1e-6


def test_model_failure_does_not_invent_prediction(monkeypatch):
    def fail_to_load():
        raise RuntimeError("simulated model loading failure")

    monkeypatch.setattr(disease_model, "_load_model", fail_to_load)

    result = disease_model.TomatoDiseaseModel().predict(
        Image.new("RGB", (32, 32), "green")
    )

    assert result["status"] == "error"
    assert result["predicted_class"] is None
    assert result["confidence"] is None
    assert result["probabilities"] == {}
    assert result["reason"] == "model_error"
    assert result["model_version"] == (
        f"{disease_model.MODEL_ID}@{disease_model.MODEL_REVISION}"
    )
    assert result["inference_time_ms"] >= 0
