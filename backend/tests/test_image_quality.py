import pytest
from app.services.reliability.vision_reliability import compute_vision_reliability
from app.services.vision.image_quality import assess_image_quality
from app.utils.sample_images import make_images


@pytest.fixture(scope="module")
def imgs():
    return make_images()


def q(imgs, name):
    return assess_image_quality(imgs[name])


def test_good_images_score_high(imgs):
    for name in ("healthy", "stressed"):
        r = q(imgs, name)
        assert r["overall"] > 0.85 and r["issues"] == [], (name, r)


def test_dark_image(imgs):
    r = q(imgs, "dark")
    assert "too_dark" in r["issues"] and r["overall"] <= 0.4


def test_blurry_image(imgs):
    r = q(imgs, "blurry")
    assert "blurry" in r["issues"] and r["overall"] <= 0.4


def test_blocked_image(imgs):
    r = q(imgs, "blocked")
    assert "blocked" in r["issues"] and r["overall"] <= 0.4


def test_overexposed_image(imgs):
    r = q(imgs, "overexposed")
    assert "overexposed" in r["issues"]
    assert r["overall"] < q(imgs, "healthy")["overall"]


def test_confident_prediction_on_bad_image_is_discounted(imgs):
    rel = compute_vision_reliability(q(imgs, "blurry"), 0.92)
    assert rel["effective_confidence"] < 0.5 and rel["trusted"] is False
    good = compute_vision_reliability(q(imgs, "healthy"), 0.92)
    assert good["trusted"] is True and good["effective_confidence"] > 0.8


def test_no_confidence_gives_none(imgs):
    assert compute_vision_reliability(q(imgs, "healthy"), None)["effective_confidence"] is None


def test_quality_scores_stay_within_zero_and_one(imgs):
    for name in imgs:
        result = q(imgs, name)
        assert 0.0 <= result["overall"] <= 1.0
        assert all(0.0 <= score <= 1.0 for score in result["scores"].values())


def test_grayscale_image_is_supported():
    from PIL import Image

    img = Image.new("L", (64, 64), color=128)
    result = assess_image_quality(img)

    assert result["metrics"]["width"] == 64
    assert result["metrics"]["height"] == 64
    assert 0.0 <= result["overall"] <= 1.0
    assert all(0.0 <= score <= 1.0 for score in result["scores"].values())


def test_tiny_image_has_finite_quality_values():
    import math
    from PIL import Image

    img = Image.new("RGB", (2, 2), color=(80, 120, 60))
    result = assess_image_quality(img)

    assert math.isfinite(result["metrics"]["blur_variance"])
    assert math.isfinite(result["overall"])
    assert all(math.isfinite(score) for score in result["scores"].values())
