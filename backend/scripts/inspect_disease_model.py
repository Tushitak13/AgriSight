
from transformers import AutoImageProcessor, AutoModelForImageClassification

MODEL_ID = "neghani/plantvillage-mobilenetv2"
MODEL_REVISION = "v1.0"


def main():
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

    labels = model.config.id2label

    print("\nModel loaded successfully.")
    print("Model:", MODEL_ID)
    print("Number of classes:", model.config.num_labels)
    print("Expected input size:", processor.size)
    print("\nAll model labels:")

    for class_id in sorted(labels, key=int):
        label = labels[class_id]
        print(f"{class_id}: {label}")

    tomato_labels = [
        labels[class_id]
        for class_id in sorted(labels, key=int)
        if labels[class_id].startswith("Tomato___")
    ]

    print(f"\nTomato classes found: {len(tomato_labels)}")
    for label in tomato_labels:
        print(" -", label)


if __name__ == "__main__":
    main()
