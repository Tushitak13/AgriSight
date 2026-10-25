
from pathlib import Path

import torch
from PIL import Image, ImageOps
from transformers import (
    AutoImageProcessor,
    AutoModelForImageClassification,
)

MODEL_ID = "neghani/plantvillage-mobilenetv2"
MODEL_REVISION = "v1.0"

IMAGE_PATH = (
    Path(__file__).resolve().parent.parent
    / "test_images"
    / "tomato_leaf.jpg"
)

# Provisional testing threshold only; validate before production use.
MIN_CONFIDENCE = 0.60


def load_model():
    """Load the model and its matching image processor."""
    print("Loading model processor...")
    processor = AutoImageProcessor.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
    )

    print("Loading classification model...")
    model = AutoModelForImageClassification.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
    )

    model.eval()
    return processor, model


def predict_image(image_path: Path, processor, model) -> dict:
    """Run classification and return scores plus a cautious decision."""
    if not image_path.is_file():
        raise FileNotFoundError(
            f"Image not found: {image_path}\n"
            "Place the image at backend/test_images/tomato_leaf.jpg"
        )

    # Load the image safely and correct phone-camera orientation.
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")

    inputs = processor(images=image, return_tensors="pt")

    with torch.inference_mode():
        logits = model(**inputs).logits
        probabilities = torch.softmax(logits, dim=-1)[0]

    labels = model.config.id2label

    # Get the five highest-scoring classes across all crops.
    top_scores, top_ids = torch.topk(
        probabilities,
        k=min(5, len(labels)),
    )

    top_predictions = []
    for score, class_id in zip(
        top_scores.tolist(),
        top_ids.tolist(),
    ):
        label = labels[class_id]
        crop = label.split("___", 1)[0]

        top_predictions.append({
            "class": label,
            "crop": crop,
            "score": score,
        })

    # Find the highest-scoring tomato class separately.
    tomato_predictions = [
        {
            "class": labels[class_id],
            "score": probabilities[class_id].item(),
        }
        for class_id in range(len(labels))
        if labels[class_id].startswith("Tomato___")
    ]

    best_tomato = (
        max(tomato_predictions, key=lambda item: item["score"])
        if tomato_predictions
        else None
    )

    best_overall = top_predictions[0]
    top_is_tomato = best_overall["crop"] == "Tomato"

    # Conservative provisional decision for this smoke test.
    if not top_is_tomato:
        status = "uncertain"
        message = (
            "The top prediction belongs to another crop. "
            "Do not treat the tomato-class ranking as a diagnosis."
        )
    elif best_overall["score"] < MIN_CONFIDENCE:
        status = "uncertain"
        message = (
            "The top score is below the provisional threshold. "
            "Manual review is recommended."
        )
    else:
        status = "model_prediction"
        message = (
            "This is a model prediction, not a confirmed diagnosis. "
            "Validate the result before making treatment decisions."
        )

    return {
        "image": image_path.name,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "num_classes": model.config.num_labels,
        "top_predictions": top_predictions,
        "best_overall": best_overall,
        "best_tomato": best_tomato,
        "status": status,
        "message": message,
    }


def main():
    if not IMAGE_PATH.is_file():
        raise FileNotFoundError(
            f"Image not found: {IMAGE_PATH}\n"
            "Place a tomato-leaf image at "
            "backend/test_images/tomato_leaf.jpg"
        )

    processor, model = load_model()
    result = predict_image(IMAGE_PATH, processor, model)

    print(f"\nImage: {result['image']}")
    print(f"Model: {result['model_id']} ({result['model_revision']})")
    print(f"Number of classes: {result['num_classes']}")

    print("\nTop 5 model predictions:")
    for item in result["top_predictions"]:
        print(
            f"{item['class']}: {item['score']:.4f} "
            f"(crop: {item['crop']})"
        )

    print("\nDecision:")
    best = result["best_overall"]
    print(f"Top overall class: {best['class']} ({best['score']:.2%})")

    tomato = result["best_tomato"]
    if tomato:
        print(
            f"Top tomato class: {tomato['class']} "
            f"({tomato['score']:.2%})"
        )
    else:
        print("No tomato classes were found in the model labels.")

    print(f"Status: {result['status'].upper()}")
    print(result["message"])


if __name__ == "__main__":
    main()
