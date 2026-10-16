"""Image quality assessment (numpy + Pillow only, no OpenCV).
Measures blur, brightness, contrast, exposure clipping, occlusion, plant coverage, resolution."""
import numpy as np
from PIL import Image

from app.utils import constants as K


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _ramp(x: float, lo: float, hi: float) -> float:
    """0 at/below lo, 1 at/above hi."""
    return _clamp((x - lo) / (hi - lo))


def blocked_fraction(luma: np.ndarray, grid: int = 8) -> float:
    """Fraction of grid blocks that are flat AND very dark/bright (lens covered, wall, glare)."""
    h, w = luma.shape
    bh, bw = h // grid, w // grid
    if bh < 2 or bw < 2:
        return 0.0
    blocks = luma[: bh * grid, : bw * grid].reshape(grid, bh, grid, bw)
    std = blocks.std(axis=(1, 3))
    mean = blocks.mean(axis=(1, 3))
    return float(((std < 3.0) & ((mean < 25) | (mean > 235))).mean())


def assess_image_quality(img: Image.Image) -> dict:
    width, height = img.size
    rgb = img.convert("RGB")
    rgb.thumbnail((K.ANALYSIS_MAX_SIDE, K.ANALYSIS_MAX_SIDE))
    a = np.asarray(rgb, dtype=np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    luma = 0.299 * r + 0.587 * g + 0.114 * b

    brightness = float(luma.mean())
    contrast = float(luma.std())
    lap = (-4 * luma[1:-1, 1:-1] + luma[:-2, 1:-1] + luma[2:, 1:-1]
           + luma[1:-1, :-2] + luma[1:-1, 2:])
    blur_var = float(lap.var())
    clip = float(((luma <= 5) | (luma >= 250)).mean())
    occlusion = blocked_fraction(luma)
    coverage = float(((2 * g - r - b) > 20).mean())   # Excess-Green vegetation proxy

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
        coverage=_ramp(coverage, *K.COVERAGE_RANGE) if K.REQUIRE_PLANT_COVERAGE else 1.0,
        resolution=_ramp(min(width, height), *K.RESOLUTION_RANGE),
    )
    overall = sum(K.IMAGE_QUALITY_WEIGHTS[k] * v for k, v in scores.items())
    if min(scores["blur"], scores["brightness"], scores["occlusion"]) < K.CRITICAL_QUALITY_FLOOR:
        overall = min(overall, K.CRITICAL_QUALITY_CAP)   # one fatal defect ruins the image

    t = K.ISSUE_THRESHOLD
    issues = []
    if scores["brightness"] < t:
        issues.append("too_dark" if brightness < lo_ok else "overexposed")
    if scores["blur"] < t:
        issues.append("blurry")
    if scores["contrast"] < t:
        issues.append("low_contrast")
    if scores["exposure"] < t:
        issues.append("clipped_exposure")
    if scores["occlusion"] < t:
        issues.append("blocked")
    if scores["coverage"] < t:
        issues.append("poor_framing")
    if scores["resolution"] < t:
        issues.append("low_resolution")

    return dict(
        metrics=dict(brightness=round(brightness, 2), contrast=round(contrast, 2),
                     blur_variance=round(blur_var, 2), clipped_fraction=round(clip, 4),
                     blocked_fraction=round(occlusion, 4), plant_coverage=round(coverage, 4),
                     width=width, height=height),
        scores={k: round(v, 3) for k, v in scores.items()},
        overall=round(overall, 3), issues=issues,
    )
