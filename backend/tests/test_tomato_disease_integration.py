from PIL import Image
import io

from app.services.vision import vision_service


class FakeTomatoModel:
    name = "fake_tomato_model"

    def __init__(self, result):
        self.result = result

    def predict(self, img):
        return self.result


def image_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (128, 128), "green").save(buf, format="JPEG")
    return buf.getvalue()


def test_service_accepts_confident_tomato_prediction(client, monkeypatch):
    fake_result = {
        "visual_state": "possible_disease",
        "prediction": "Early_blight",
        "confidence": 0.95,
        "status": "success",
        "reason": None,
        "predicted_class": "Tomato___Early_blight",
        "probabilities": {"Tomato___Early_blight": 0.95},
    }
    monkeypatch.setattr(
        vision_service, "_model", FakeTomatoModel(fake_result)
    )

    response = client.post(
        "/api/vision/analyze",
        files={"file": ("tomato.jpg", image_bytes(), "image/jpeg")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["prediction"] == "Early_blight"
    assert data["model_confidence"] == 0.95
    assert data["model_name"] == "fake_tomato_model"


def test_service_preserves_uncertain_adapter_result(client, monkeypatch):
    fake_result = {
        "visual_state": "uncertain_crop",
        "prediction": "unknown",
        "confidence": 0.75,
        "status": "uncertain",
        "reason": "non_tomato_top_prediction",
        "predicted_class": None,
        "probabilities": {"Apple___healthy": 0.75},
    }
    monkeypatch.setattr(
        vision_service, "_model", FakeTomatoModel(fake_result)
    )

    response = client.post(
        "/api/vision/analyze",
        files={"file": ("other.jpg", image_bytes(), "image/jpeg")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["prediction"] == "unknown"
    assert data["visual_state"] == "uncertain_crop"
    assert data["model_name"] == "fake_tomato_model"
