"""Runtime settings. Domain constants (ranges, thresholds, weights) live in utils/constants.py."""
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agrisight.db")
DEFAULT_DEVICE_ID = "esp32-01"
MAX_FUTURE_SKEW_SECONDS = 300   # reject readings stamped further in the future than this
RELIABILITY_WINDOW = 20         # readings used for rolling statistics

# Uploaded camera images go to AgriSight/data/raw (override with VISION_UPLOAD_DIR env var)
VISION_UPLOAD_DIR = Path(os.getenv("VISION_UPLOAD_DIR",
                                   Path(__file__).resolve().parents[2] / "data" / "raw"))
