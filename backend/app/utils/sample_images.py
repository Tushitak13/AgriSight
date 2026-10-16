"""Synthetic plant-like test images (no real photos needed).
Run:  python -m app.utils.sample_images   -> writes JPGs to AgriSight/data/sample"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def _plant(stressed_fraction: float, seed: int = 1, size=(640, 480)) -> Image.Image:
    rng = np.random.default_rng(seed)
    w, h = size
    bg = np.full((h, w, 3), 118, dtype=np.float32)            # neutral grey backdrop
    bg += rng.normal(0, 10, (h, w, 1))                         # texture
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for _ in range(140):
        cx, cy = rng.integers(0, w), rng.integers(0, h)
        rw, rh = rng.integers(25, 70), rng.integers(12, 30)
        if rng.random() < stressed_fraction:
            col = (int(rng.integers(190, 225)), int(rng.integers(150, 185)), int(rng.integers(20, 60)))
        else:
            col = (int(rng.integers(30, 70)), int(rng.integers(130, 185)), int(rng.integers(30, 70)))
        d.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=col, outline=(20, 60, 20))
        d.line([cx - rw, cy, cx + rw, cy], fill=(15, 50, 15), width=1)  # leaf vein
    arr = np.asarray(img, dtype=np.float32) + rng.normal(0, 6, (h, w, 3))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def make_images() -> dict[str, Image.Image]:
    healthy = _plant(0.03, seed=1)
    stressed = _plant(0.75, seed=2)
    arr = np.asarray(healthy, dtype=np.float32)
    blocked = arr.copy()
    blocked[:, : int(blocked.shape[1] * 0.65)] = 0             # lens mostly covered
    return {
        "healthy": healthy,
        "stressed": stressed,
        "dark": Image.fromarray((arr * 0.12).astype(np.uint8)),
        "blurry": healthy.filter(ImageFilter.GaussianBlur(9)),
        "blocked": Image.fromarray(blocked.astype(np.uint8)),
        "overexposed": Image.fromarray(np.clip(arr * 2.4 + 40, 0, 255).astype(np.uint8)),
    }


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[3] / "data" / "sample"
    out.mkdir(parents=True, exist_ok=True)
    for name, im in make_images().items():
        im.save(out / f"{name}.jpg", quality=92)
        print("wrote", out / f"{name}.jpg")
