from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
import math

root = Path("data")
files = []
for folder in [root / "raw", root / "sample"]:
    if folder.exists():
        files.extend(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in
            {".jpg", ".jpeg", ".png", ".webp"}
        )

if not files:
    raise SystemExit("No image files found.")

cell_w, cell_h = 240, 220
columns = 4
rows = math.ceil(len(files) / columns)
sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
draw = ImageDraw.Draw(sheet)

for i, path in enumerate(files):
    x = (i % columns) * cell_w
    y = (i // columns) * cell_h
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((cell_w - 16, 170))
            sheet.paste(im, (x + (cell_w - im.width) // 2, y + 5))
            label = f"{path.parent.name}/{path.name}"
            draw.text((x + 6, y + 180), label[:34], fill="black")
            draw.text((x + 6, y + 198), f"{Image.open(path).size}", fill="black")
    except Exception as e:
        draw.text((x + 6, y + 20), f"Cannot open: {path.name}", fill="red")

out = Path("model_evaluation") / "existing_images_contact_sheet.jpg"
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out, quality=90)
print(f"Images inspected: {len(files)}")
print(f"Contact sheet: {out.resolve()}")
