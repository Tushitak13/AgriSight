
"""AgriSight vision pipeline: YOLO26 + MobileNetV2 + OpenCV."""

import io
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
import torch
from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session
from torch import nn
from torchvision import models, transforms
from ultralytics import YOLO

from app import config
from app.models.vision import VisionObservation
from app.services.ingestion.sensor_service import utcnow
from app.services.reliability.vision_reliability import compute_vision_reliability
from app.services.vision.image_quality import assess_image_quality
from app.utils import constants as K


ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}

CLASS_NAMES = [
    "Early Blight",
    "Black Spot",
    "Late Blight",
    "Leaf Mold",
    "Bacterial Spot",
    "Target Spot",
    "Healthy",
]

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
YOLO_CHECKPOINT = MODEL_DIR / "yolo26_best.pt"
MOBILENET_CHECKPOINT = MODEL_DIR / "mobilenetv2_finetuned.pth"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Provisional threshold for sending predictions to review.
# Validate this value against held-out data before production use.
VISION_REVIEW_CONFIDENCE_THRESHOLD = 0.50


class VisionError(ValueError):
    pass


class VisionModel(Protocol):
    name: str

    def predict(self, img: Image.Image) -> dict:
        """Return visual_state, prediction and confidence."""


class HeuristicVegetationModel:
    """Simple deterministic model for existing tests."""

    name = "placeholder_color_heuristic"

    def predict(self, img: Image.Image) -> dict:
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
                "detections": [],
            }

        ratio = stressed / total

        if ratio > 0.35:
            return {
                "visual_state": "possible_stress",
                "prediction": "stressed",
                "confidence": round(min(0.95, 0.5 + ratio), 3),
                "detections": [],
            }

        return {
            "visual_state": "healthy_appearance",
            "prediction": "healthy",
            "confidence": round(min(0.95, 0.6 + (0.35 - ratio)), 3),
            "detections": [],
        }


class CombinedVisionModel:
    """YOLO26 detection + MobileNetV2 crop classification + OpenCV."""

    name = "yolo26_mobilenetv2_opencv"

    def __init__(self):
        if not YOLO_CHECKPOINT.is_file():
            raise RuntimeError(f"YOLO26 checkpoint not found: {YOLO_CHECKPOINT}")

        if not MOBILENET_CHECKPOINT.is_file():
            raise RuntimeError(
                f"MobileNetV2 checkpoint not found: {MOBILENET_CHECKPOINT}"
            )

        self.detector = YOLO(str(YOLO_CHECKPOINT))

        checkpoint = torch.load(
            MOBILENET_CHECKPOINT,
            map_location="cpu",
            weights_only=False,
        )

        if checkpoint.get("class_names") != CLASS_NAMES:
            raise RuntimeError(
                "MobileNetV2 class order does not match the expected class list."
            )

        self.classifier = models.mobilenet_v2(weights=None)
        self.classifier.classifier[1] = nn.Linear(
            self.classifier.last_channel, len(CLASS_NAMES)
        )
        self.classifier.load_state_dict(checkpoint["model_state_dict"])
        self.classifier.to(DEVICE)
        self.classifier.eval()

        input_size = int(checkpoint.get("input_size", 224))

        # Confirm normalization matches the original training pipeline.
        self.preprocess = transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    @torch.inference_mode()
    def _classify(self, crop: Image.Image) -> tuple[str, float]:
        tensor = self.preprocess(crop.convert("RGB")).unsqueeze(0).to(DEVICE)
        probabilities = torch.softmax(self.classifier(tensor), dim=1)[0]
        class_index = int(torch.argmax(probabilities).item())
        confidence = float(probabilities[class_index].item())
        return CLASS_NAMES[class_index], confidence

    def predict(self, img: Image.Image) -> dict:
        rgb = np.asarray(img.convert("RGB"))
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        results = self.detector.predict(
            source=bgr,
            verbose=False,
            device=str(DEVICE),
        )

        result = results[0]
        detections = []

        if result.boxes is not None and len(result.boxes) > 0:
            boxes = result.boxes.xyxy.cpu().numpy()
            detector_scores = result.boxes.conf.cpu().numpy()
            detector_classes = result.boxes.cls.cpu().numpy().astype(int)

            height, width = bgr.shape[:2]

            for box, det_conf, det_class in zip(
                boxes, detector_scores, detector_classes
            ):
                if not 0 <= det_class < len(CLASS_NAMES):
                    continue

                x1, y1, x2, y2 = map(int, box)

                x1 = max(0, min(x1, width - 1))
                x2 = max(0, min(x2, width))
                y1 = max(0, min(y1, height - 1))
                y2 = max(0, min(y2, height))

                if x2 <= x1 or y2 <= y1:
                    continue

                crop_bgr = bgr[y1:y2, x1:x2]
                crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
                crop = Image.fromarray(crop_rgb)

                mobile_label, mobile_conf = self._classify(crop)
                yolo_label = CLASS_NAMES[det_class]

                # Provisional fusion score, not a calibrated probability.
                combined_conf = float(np.sqrt(float(det_conf) * mobile_conf))
                agrees = yolo_label == mobile_label

                detections.append({
                    "box": [x1, y1, x2, y2],
                    "yolo_label": yolo_label,
                    "yolo_confidence": round(float(det_conf), 4),
                    "mobilenet_label": mobile_label,
                    "mobilenet_confidence": round(mobile_conf, 4),
                    "agreement": agrees,
                    "combined_confidence": round(combined_conf, 4),
                })

        if detections:
            best = max(detections, key=lambda item: item["yolo_confidence"])

            if not best["agreement"]:
                visual_state = "model_disagreement_review"
            elif (
                best["combined_confidence"]
                < VISION_REVIEW_CONFIDENCE_THRESHOLD
            ):
                visual_state = "low_confidence_review"
            else:
                visual_state = "models_agree"

            return {
                "visual_state": visual_state,
                "prediction": best["mobilenet_label"],
                "confidence": best["combined_confidence"],
                "detections": detections,
            }

        # Fallback: classify the entire image when YOLO finds no boxes.
        label, confidence = self._classify(img)

        if confidence < VISION_REVIEW_CONFIDENCE_THRESHOLD:
            visual_state = "low_confidence_review"
        else:
            visual_state = "no_yolo_detection_mobilenet_fallback"

        return {
            "visual_state": visual_state,
            "prediction": label,
            "confidence": confidence,
            "detections": [],
        }


_model: VisionModel | None = None


@lru_cache(maxsize=1)
def _load_default_model() -> VisionModel:
    return CombinedVisionModel()


def get_model() -> VisionModel:
    global _model
    if _model is None:
        _model = _load_default_model()
    return _model


def set_model(model: VisionModel) -> None:
    """Allow tests or other integrations to inject a vision model."""
    global _model
    _model = model


def analyze_upload(db: Session, device_id: str, raw: bytes) -> VisionObservation:
    if len(raw) > K.MAX_IMAGE_BYTES:
        raise VisionError("image too large (max 8 MB)")

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:
        raise VisionError("file is not a valid image") from exc

    ext = ALLOWED_FORMATS.get((img.format or "").upper())
    if ext is None:
        raise VisionError("unsupported image format (use JPEG, PNG or WEBP)")

    img = ImageOps.exif_transpose(img).convert("RGB")

    quality = assess_image_quality(img)
    model = get_model()
    pred = model.predict(img)

    rel = compute_vision_reliability(quality, pred.get("confidence"))

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
        visual_state=pred["visual_state"],
        prediction=pred["prediction"],
        model_confidence=pred.get("confidence"),
        vision_reliability=rel["vision_reliability"],
        effective_confidence=rel["effective_confidence"],
        trusted=(rel["trusted"] and pred.get("visual_state") != "model_disagreement_review"),
        detections=pred.get("detections", []),
    )

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_latest_observation(db: Session, device_id: str):
    return db.scalars(
        select(VisionObservation)
        .where(VisionObservation.device_id == device_id)
        .order_by(
            VisionObservation.captured_at.desc(),
            VisionObservation.id.desc(),
        )
        .limit(1)
    ).first()


def get_observation_history(db: Session, device_id: str, limit: int = 50):
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

