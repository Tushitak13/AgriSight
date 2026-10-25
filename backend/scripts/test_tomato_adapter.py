
from pathlib import Path

from PIL import Image

from app.services.vision.tomato_disease_model import TomatoDiseaseModel

image_path = (
    Path(__file__).resolve().parent.parent
    / "test_images"
    / "tomato_leaf.jpg"
)

if not image_path.is_file():
    raise FileNotFoundError(f"Test image not found: {image_path}")

with Image.open(image_path) as image:
    result = TomatoDiseaseModel().predict(image)

print("Adapter result:")
for key, value in result.items():
    print(f"{key}: {value}")
