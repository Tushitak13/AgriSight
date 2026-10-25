"""Image quality assessment using NumPy, Pillow, and OpenCV.
Measures blur, brightness, contrast, exposure clipping, occlusion,
plant coverage, and resolution.
"""

import cv2
import numpy as np
from PIL import Image

from app.utils import constants as K


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _ramp(x: float, lo: float, hi: float) -> float:
    """Return 0 at/below lo and 1 at/above hi."""
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return _clamp((x - lo) / (hi - lo))


def blocked_fraction(luma: np.ndarray, grid: int = 8) -> float:
    """Estimate flat, extremely dark or bright image blocks."""
    h, w = luma.shape
    bh, bw = h // grid, w // grid

    if bh < 2 or bw < 2:
        return 0.0

    blocks = luma[:bh * grid, :bw * grid].reshape(
        grid, bh, grid, bw
    )
    std = blocks.std(axis=(1, 3))
    mean = blocks.mean(axis=(1, 3))

    return float(
        ((std < 3.0) & ((mean < 25) | (mean > 235))).mean()
    )


def assess_image_quality(img: Image.Image) -> dict:
    """Calculate image-quality metrics, scores, and potential issues."""
    width, height = img.size

    rgb = img.convert("RGB")
    rgb.thumbnail((K.ANALYSIS_MAX_SIDE, K.ANALYSIS_MAX_SIDE))

    a = np.asarray(rgb, dtype=np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    luma = 0.299 * r + 0.587 * g + 0.114 * b

    brightness = float(luma.mean())
    contrast = float(luma.std())

    # Exposure clipping, occlusion, and vegetation coverage.
    clip = float(((luma <= 5) | (luma >= 250)).mean())
    occlusion = blocked_fraction(luma)
    coverage = float(((2 * g - r - b) > 20).mean())

    # Avoid an invalid blur estimate for images smaller than 3 x 3.
    if luma.shape[0] < 3 or luma.shape[1] < 3:
        blur_var = 0.0
    else:
        gray = np.asarray(rgb.convert("L"), dtype=np.uint8)
        blur_var = float(
            cv2.Laplacian(gray, cv2.CV_64F).var()
        )

    lo_ok, hi_ok = K.BRIGHTNESS_OK
    lo_lim, hi_lim = K.BRIGHTNESS_LIMITS

    if brightness < lo_ok:
        s_bright = _ramp(brightness, lo_lim, lo_ok)
    elif brightness > hi_ok:
        s_bright = 1 - _ramp(brightness, hi_ok, hi_lim)
    else:
        s_bright = 1.0

    scores = dict(
        blur=_ramp(blur_var, *K.BLUR_VAR_RANGE),
        brightness=s_bright,
        contrast=_ramp(contrast, *K.CONTRAST_STD_RANGE),
        exposure=1 - _ramp(clip, *K.CLIP_FRAC_RANGE),
        occlusion=1 - _ramp(occlusion, *K.OCCLUSION_FRAC_RANGE),
        coverage=(
            _ramp(coverage, *K.COVERAGE_RANGE)
            if K.REQUIRE_PLANT_COVERAGE else 1.0
        ),
        resolution=_ramp(min(width, height), *K.RESOLUTION_RANGE),
    )

    overall = sum(
        K.IMAGE_QUALITY_WEIGHTS[key] * value
        for key, value in scores.items()
    )

    if min(
        scores["blur"],
        scores["brightness"],
        scores["occlusion"],
    ) < K.CRITICAL_QUALITY_FLOOR:
        overall = min(overall, K.CRITICAL_QUALITY_CAP)

    threshold = K.ISSUE_THRESHOLD
    issues = []

    if scores["brightness"] < threshold:
        issues.append("too_dark" if brightness < lo_ok else "overexposed")
    if scores["blur"] < threshold:
        issues.append("blurry")
    if scores["contrast"] < threshold:
        issues.append("low_contrast")
    if scores["exposure"] < threshold:
        issues.append("clipped_exposure")
    if scores["occlusion"] < threshold:
        issues.append("blocked")
    if scores["coverage"] < threshold:
        issues.append("poor_framing")
    if scores["resolution"] < threshold:
        issues.append("low_resolution")

    return dict(
        metrics=dict(
            brightness=round(brightness, 2),
            contrast=round(contrast, 2),
            blur_variance=round(blur_var, 2),
            clipped_fraction=round(clip, 4),
            blocked_fraction=round(occlusion, 4),
            plant_coverage=round(coverage, 4),
            width=width,
            height=height,
        ),
        scores={key: round(value, 3) for key, value in scores.items()},
        overall=round(overall, 3),
        issues=issues,
    )
