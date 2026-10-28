import csv
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.vision.vision_service import CombinedVisionModel, CLASS_NAMES

TEST_ROOT = ROOT / "external_datasets" / "PlantDoc" / "test"
OUTPUT = ROOT / "model_evaluation" / "plantdoc_test_predictions.csv"

# Only map folders with a defensible matching disease label.
FOLDER_TO_LABEL = {
    "Tomato Early blight leaf": "Early Blight",
    "Tomato leaf bacterial spot": "Bacterial Spot",
    "Tomato leaf late blight": "Late Blight",
    "Tomato mold leaf": "Leaf Mold",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def main():
    if not TEST_ROOT.is_dir():
        raise SystemExit(f"Test dataset folder not found: {TEST_ROOT}")

    for label in FOLDER_TO_LABEL.values():
        if label not in CLASS_NAMES:
            raise SystemExit(f"Unknown AgriSight class: {label}")

    folders = []
    for folder_name, label in FOLDER_TO_LABEL.items():
        folder = TEST_ROOT / folder_name
        if not folder.is_dir():
            print(f"WARNING: Missing folder, skipping: {folder}")
            continue
        folders.append((folder, label))

    if not folders:
        raise SystemExit("No mapped PlantDoc test folders were found.")

    print("Loading the actual YOLO26 + MobileNetV2 pipeline...")
    model = CombinedVisionModel()
    rows = []
    errors = []

    for folder, true_label in folders:
        files = sorted(
            path for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )
        print(f"\n{folder.name}: {len(files)} images -> {true_label}")

        for path in files:
            try:
                with Image.open(path) as source:
                    image = source.convert("RGB")
                    result = model.predict(image)

                detections = result.get("detections", [])
                best = max(
                    detections,
                    key=lambda item: item.get("yolo_confidence", 0),
                    default={},
                )

                rows.append({
                    "image": str(path.relative_to(ROOT)),
                    "true_label": true_label,
                    "predicted_label": result.get("prediction") or "unknown",
                    "visual_state": result.get("visual_state", "unknown"),
                    "confidence": result.get("confidence", ""),
                    "yolo_label": best.get("yolo_label", ""),
                    "yolo_confidence": best.get("yolo_confidence", ""),
                    "mobilenet_label": best.get("mobilenet_label", ""),
                    "models_agree": best.get("agreement", ""),
                })

            except Exception as exc:
                errors.append((str(path), str(exc)))
                print(f"ERROR: {path.name}: {exc}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "image", "true_label", "predicted_label", "visual_state",
        "confidence", "yolo_label", "yolo_confidence",
        "mobilenet_label", "models_agree",
    ]

    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    print("\n--- EVALUATION INPUT SUMMARY ---")
    print(f"Successfully evaluated: {len(rows)}")
    print(f"Failed images: {len(errors)}")
    print(f"Prediction CSV: {OUTPUT}")

    if errors:
        error_path = OUTPUT.with_name("plantdoc_inference_errors.csv")
        with error_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["image", "error"])
            writer.writerows(errors)
        print(f"Error log: {error_path}")

    if not rows:
        raise SystemExit("No images were evaluated; metrics cannot be calculated.")

    print("\nReview-state counts:")
    states = {}
    for row in rows:
        state = row["visual_state"]
        states[state] = states.get(state, 0) + 1
    for state, count in sorted(states.items()):
        print(f"  {state}: {count}")


if __name__ == "__main__":
    main()
