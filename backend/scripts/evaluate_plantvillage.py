
import csv
import random
import time
from collections import defaultdict
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

DATASET_DIR = Path(r"D:\Archive\plantvillage dataset\color")
OUTPUT_DIR = Path(r"D:\Archive\agrisight_evaluation")
MODEL_ID = "neghani/plantvillage-mobilenetv2"
REVISION = "v1.0"

SAMPLES_PER_CLASS = 20
SEED = 42

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading model...")
processor = AutoImageProcessor.from_pretrained(
    MODEL_ID, revision=REVISION
)
model = AutoModelForImageClassification.from_pretrained(
    MODEL_ID, revision=REVISION
)
model.eval()

labels = model.config.id2label
class_dirs = sorted(
    p for p in DATASET_DIR.iterdir()
    if p.is_dir() and p.name.startswith("Tomato___")
)

assert len(class_dirs) == 10, (
    f"Expected 10 tomato classes, found {len(class_dirs)}"
)

known_labels = set(labels.values())
for folder in class_dirs:
    assert folder.name in known_labels, (
        f"Unknown model label: {folder.name}"
    )

rng = random.Random(SEED)
results = []
stats = defaultdict(lambda: {
    "total": 0,
    "correct": 0,
    "non_tomato": 0,
})

print(f"Found {len(class_dirs)} tomato classes.")

for folder in class_dirs:
    images = sorted(
        p for p in folder.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )

    sample = rng.sample(
        images, min(SAMPLES_PER_CLASS, len(images))
    )

    print(f"\nEvaluating {folder.name}: {len(sample)} images")

    for path in sample:
        start = time.perf_counter()

        try:
            with Image.open(path) as img:
                image = img.convert("RGB")

            inputs = processor(
                images=image, return_tensors="pt"
            )

            with torch.inference_mode():
                logits = model(**inputs).logits
                scores = torch.softmax(logits, dim=-1)[0]

            index = int(torch.argmax(scores).item())
            predicted = labels[index]
            score = float(scores[index].item())

            correct = predicted == folder.name
            non_tomato = not predicted.startswith("Tomato___")

            stats[folder.name]["total"] += 1
            stats[folder.name]["correct"] += int(correct)
            stats[folder.name]["non_tomato"] += int(non_tomato)

            results.append({
                "image": str(path),
                "true_class": folder.name,
                "predicted_class": predicted,
                "top_score": round(score, 6),
                "correct": correct,
                "non_tomato_prediction": non_tomato,
                "inference_time_ms": round(
                    (time.perf_counter() - start) * 1000, 2
                ),
                "error": "",
            })

        except Exception as exc:
            results.append({
                "image": str(path),
                "true_class": folder.name,
                "predicted_class": "",
                "top_score": "",
                "correct": False,
                "non_tomato_prediction": "",
                "inference_time_ms": "",
                "error": str(exc),
            })
            print(f"ERROR: {path.name}: {exc}")

output_file = OUTPUT_DIR / "plantvillage_results.csv"

with output_file.open(
    "w", newline="", encoding="utf-8"
) as file:
    writer = csv.DictWriter(
        file, fieldnames=list(results[0].keys())
    )
    writer.writeheader()
    writer.writerows(results)

total = sum(s["total"] for s in stats.values())
correct = sum(s["correct"] for s in stats.values())
non_tomato = sum(s["non_tomato"] for s in stats.values())
errors = sum(bool(r["error"]) for r in results)

print("\n========== EVALUATION RESULTS ==========")
print(f"Attempted images: {len(results)}")
print(f"Successful inferences: {total}")
print(f"Errors: {errors}")

if total:
    print(f"Top-1 accuracy: {correct / total * 100:.2f}%")
    print(
        f"Non-tomato top predictions: "
        f"{non_tomato / total * 100:.2f}%"
    )

print("\nPer-class results:")
for name in sorted(stats):
    s = stats[name]
    accuracy = 100 * s["correct"] / s["total"]
    print(
        f"{name}: {accuracy:.1f}% "
        f"({s['correct']}/{s['total']}) "
        f"| non-tomato: {s['non_tomato']}"
    )

print(f"\nCSV saved to: {output_file}")
