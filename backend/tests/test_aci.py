
"""ACI tests: pure fusion maths, then the API with real sensors / experiences / images."""
import io
from types import SimpleNamespace

import pytest

from app.services.confidence.aci import aci_level, compute_aci, prediction_consistency
from app.utils import constants as K
from app.utils.sample_images import make_images
from tests.conftest import GOOD

IMGS = make_images()


def jpg_bytes(name):
    buf = io.BytesIO()
    IMGS[name].save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def upload(client, name):
    return client.post(
        "/api/vision/analyze",
        files={"file": (f"{name}.jpg", jpg_bytes(name), "image/jpeg")},
    )


# ---------------- configuration sanity

def test_weights_sum_to_one_and_every_state_has_a_favourability():
    assert sum(K.ACI_WEIGHTS.values()) == pytest.approx(1.0)
    assert sum(K.CRI_WEIGHTS.values()) == pytest.approx(1.0)
    assert sum(K.CRI_FIELD_WEIGHTS.values()) == pytest.approx(1.0)

    for field, table in K.STATE_THRESHOLDS.items():
        assert {label for _, label in table} == set(K.STATE_FAVOURABILITY[field]), field


# ---------------- pure fusion

def test_full_evidence_is_the_weighted_mean():
    r = compute_aci(
        0.91, 0.79, True,
        vision_reliability=0.84,
        prediction_confidence=0.88,
        recent_behaviour=0.90,
    )
    assert r["aci"] == pytest.approx(0.866, abs=1e-3)
    assert r["level"] == "HIGH" and r["evidence_coverage"] == 1.0
    assert r["cold_start"] is False and r["capped"] is False
    assert r["limiting_factor"] == "historical_similarity"


def test_missing_components_are_skipped_and_weights_renormalised():
    r = compute_aci(0.9, 0.8, True)

    assert r["aci"] == pytest.approx(0.86, abs=1e-3)
    assert r["evidence_coverage"] == 0.5
    assert r["components"]["vision_reliability"]["available"] is False
    assert r["components"]["sensor_reliability"]["effective_weight"] == pytest.approx(0.6)
    assert sum(c["effective_weight"] for c in r["components"].values()) == pytest.approx(
        1.0, abs=0.01
    )
    assert "no fresh camera evidence" in r["notes"]


def test_low_evidence_coverage_caps_confidence_below_high():
    r = compute_aci(
        0.934,
        0.992,
        True,
        evidence_freshness={
            "sensor_reliability": 0.24,
            "historical_similarity": 0.963,
        },
    )

    assert r["evidence_coverage"] < K.ACI_MIN_COVERAGE_FOR_HIGH
    assert r["aci"] == K.ACI_LOW_COVERAGE_CAP
    assert r["level"] == "MEDIUM"
    assert r["capped"] is True
    assert any("low_evidence_coverage" in note for note in r["notes"])


def test_sufficient_evidence_coverage_does_not_apply_coverage_cap():
    r = compute_aci(
        0.9,
        0.8,
        True,
        evidence_freshness={
            "sensor_reliability": 1.0,
            "historical_similarity": 1.0,
        },
    )

    assert r["evidence_coverage"] == pytest.approx(0.5)
    assert r["aci"] == pytest.approx(0.86)
    assert r["capped"] is False


def test_cold_start_is_skipped_and_capped_below_high():
    r = compute_aci(0.95, 0.0, False)

    assert r["cold_start"] is True and r["capped"] is True
    assert r["aci"] == K.ACI_COLD_START_CAP < K.ACI_HIGH
    assert r["components"]["historical_similarity"]["available"] is False


def test_cold_start_cap_does_not_raise_a_low_score():
    r = compute_aci(0.5, 0.0, False)

    assert r["aci"] == 0.5
    assert r["capped"] is False


def test_unfamiliar_situation_counts_as_zero_history_not_skipped():
    r = compute_aci(0.95, 0.0, True)

    assert r["components"]["historical_similarity"]["available"] is True
    assert r["aci"] < 0.6 and r["level"] == "LOW"
    assert r["limiting_factor"] == "historical_similarity"
    assert r["cold_start"] is False


def test_bad_image_pulls_confidence_down_even_if_model_is_sure():
    good = compute_aci(
        0.9, 0.8, True,
        vision_reliability=0.95,
        prediction_confidence=0.9 * 0.95,
    )
    bad = compute_aci(
        0.9, 0.8, True,
        vision_reliability=0.40,
        prediction_confidence=0.92 * 0.40,
    )

    assert bad["aci"] < good["aci"] - 0.15
    assert bad["limiting_factor"] in (
        "vision_reliability",
        "prediction_confidence",
    )


def test_inputs_are_clamped_to_unit_range():
    r = compute_aci(
        1.7, 5.0, True,
        vision_reliability=-2.0,
    )

    assert 0.0 <= r["aci"] <= 1.0
    assert r["components"]["sensor_reliability"]["value"] == 1.0
    assert r["components"]["vision_reliability"]["value"] == 0.0


def test_level_boundaries():
    assert aci_level(K.ACI_HIGH) == "HIGH"
    assert aci_level(K.ACI_HIGH - 0.001) == "MEDIUM"
    assert aci_level(K.ACI_LOW) == "MEDIUM"
    assert aci_level(K.ACI_LOW - 0.001) == "LOW"


def _obs(*labels, trusted=True):
    return [
        SimpleNamespace(prediction=prediction, trusted=trusted)
        for prediction in labels
    ]


def test_prediction_consistency():
    assert prediction_consistency(
        _obs("healthy", "healthy", "healthy")
    ) == 1.0

    assert prediction_consistency(
        _obs("healthy", "stressed", "healthy", "stressed", "healthy")
    ) == 0.6

    assert prediction_consistency(_obs("healthy")) is None
    assert prediction_consistency(
        _obs("healthy", "healthy", trusted=False)
    ) is None

    mixed = (
        _obs("healthy")
        + _obs("stressed", "stressed", trusted=False)
        + _obs("healthy")
    )
    assert prediction_consistency(mixed) == 1.0

    only_recent = _obs(*(["stressed"] * 5 + ["healthy"] * 20))
    assert prediction_consistency(only_recent) == 1.0


# ---------------- API

OTHER = dict(
    temperature=5,
    humidity=20,
    soil=90,
    rain=80,
    water=300,
    light=5,
)


def make_exp(client, condition, status="SUCCESSFUL", **over):
    body = dict(
        condition=condition,
        decision="irrigation_needed",
        intervention="light_irrigation",
        outcome={"status": status},
        **over,
    )
    assert client.post("/api/experiences", json=body).status_code == 201


def test_aci_404_without_readings(client):
    assert client.get("/api/aci/current").status_code == 404


def test_aci_cold_start_api(client):
    client.post("/api/sensors/readings", json=GOOD)
    d = client.get("/api/aci/current").json()

    assert d["cold_start"] is True and d["capped"] is True
    assert d["aci"] == K.ACI_COLD_START_CAP
    assert d["level"] == "MEDIUM"
    assert d["components"]["historical_similarity"]["available"] is False
    assert d["vision_used"] is False
    assert d["n_experiences"] == 0
    assert d["novel_condition"] is False


def test_aci_rises_with_similar_history(client):
    client.post("/api/sensors/readings", json=GOOD)
    cold = client.get("/api/aci/current").json()["aci"]

    for _ in range(3):
        make_exp(client, GOOD)

    d = client.get("/api/aci/current").json()

    assert d["cold_start"] is False and d["n_similar"] == 3
    assert d["aci"] > cold
    assert d["aci"] >= K.ACI_HIGH and d["level"] == "HIGH"
    assert d["components"]["historical_similarity"]["value"] == 1.0


def test_aci_drops_when_history_exists_but_nothing_is_similar(client):
    client.post("/api/sensors/readings", json=GOOD)

    for _ in range(5):
        make_exp(client, OTHER)

    d = client.get("/api/aci/current").json()

    assert d["n_experiences"] == 5 and d["n_similar"] == 0
    assert d["novel_condition"] is True
    assert d["components"]["historical_similarity"]["value"] == 0.0
    assert d["limiting_factor"] == "historical_similarity"
    assert d["aci"] < K.ACI_COLD_START_CAP


def test_novel_condition_needs_enough_history(client):
    client.post("/api/sensors/readings", json=GOOD)

    for _ in range(K.UNEXPLAINED_MIN_EXPERIENCES - 1):
        make_exp(client, OTHER)

    assert client.get("/api/aci/current").json()["novel_condition"] is False


def test_aci_uses_fresh_camera_evidence(client):
    client.post("/api/sensors/readings", json=GOOD)

    for _ in range(3):
        make_exp(client, GOOD)

    assert upload(client, "healthy").status_code == 201

    d = client.get("/api/aci/current").json()
    assert d["vision_used"] is True
    assert d["vision_observation_id"] is not None

    components = d["components"]
    assert components["vision_reliability"]["available"]
    assert components["prediction_confidence"]["available"]
    assert components["recent_behaviour"]["available"] is False

    upload(client, "healthy")

    assert (
        client.get("/api/aci/current").json()
        ["components"]["recent_behaviour"]["value"]
        == 1.0
    )

    assert (
        client.get("/api/aci/current?include_vision=false").json()
        ["vision_used"]
        is False
    )


def test_bad_image_lowers_aci_and_flip_flopping_lowers_behaviour(client):
    client.post("/api/sensors/readings", json=GOOD)

    for _ in range(3):
        make_exp(client, GOOD)

    upload(client, "healthy")
    good = client.get("/api/aci/current").json()

    upload(client, "dark")
    bad = client.get("/api/aci/current").json()

    assert bad["aci"] < good["aci"]
    assert bad["components"]["vision_reliability"]["value"] < 0.5

    upload(client, "stressed")
    flip = client.get("/api/aci/current").json()

    assert flip["components"]["recent_behaviour"]["value"] == 0.5


def test_stale_camera_evidence_is_ignored(client, monkeypatch):
    client.post("/api/sensors/readings", json=GOOD)
    upload(client, "healthy")

    assert client.get("/api/aci/current").json()["vision_used"] is True

    monkeypatch.setattr(K, "ACI_VISION_MAX_AGE_MINUTES", -1)

    assert client.get("/api/aci/current").json()["vision_used"] is False


def test_spiked_sensor_is_left_out_of_similarity_matching(client):
    make_exp(client, GOOD)

    for soil in (55, 56, 54, 55, 56, 55, 54, 55, 56, 55):
        client.post(
            "/api/sensors/readings",
            json=dict(GOOD, soil=soil),
        )

    client.post(
        "/api/sensors/readings",
        json=dict(GOOD, soil=5),
    )

    d = client.get("/api/aci/current").json()

    assert "soil" in d["excluded_fields"]
    assert (
        d["components"]["historical_similarity"]["value"]
        <= 0.7 + 1e-9
    )


# ---------------- camera trigger now uses ACI

def test_trigger_reports_aci_and_stays_quiet_on_cold_start(client):
    client.post("/api/sensors/readings", json=GOOD)

    d = client.get("/api/vision/trigger").json()

    assert d["aci"] == K.ACI_COLD_START_CAP
    assert d["trigger"] is False and d["reasons"] == []


def test_trigger_fires_for_unfamiliar_conditions(client):
    client.post("/api/sensors/readings", json=GOOD)

    for _ in range(5):
        make_exp(client, OTHER)

    d = client.get("/api/vision/trigger").json()

    assert d["trigger"] is True
    assert "unexplained_condition" in d["reasons"]


def test_trigger_ignores_camera_evidence_in_its_own_aci(client):
    client.post("/api/sensors/readings", json=GOOD)

    before = client.get("/api/vision/trigger").json()["aci"]

    upload(client, "healthy")

    assert client.get("/api/vision/trigger").json()["aci"] == before


def test_trigger_without_readings_has_no_aci(client):
    d = client.get("/api/vision/trigger").json()

    assert d["trigger"] is True
    assert d["reasons"] == ["no_sensor_data"]
    assert d["aci"] is None


# ---------------- Evidence Decay Logic + Mahalanobis novelty

from app.services.confidence.evidence_decay import decay_factor
from app.services.confidence.mahalanobis import mahalanobis_novelty


def test_edl_half_life_and_floor():
    assert decay_factor(0, 6) == pytest.approx(1.0)
    assert decay_factor(6, 6) == pytest.approx(0.5)
    assert decay_factor(10000, 6, floor=0.05) == pytest.approx(0.05)


def test_edl_reduces_stale_sensor_weight_without_changing_component_value():
    fresh = compute_aci(
        0.8,
        0.8,
        True,
        evidence_freshness={"sensor_reliability": 1.0},
    )
    stale = compute_aci(
        0.8,
        0.8,
        True,
        evidence_freshness={"sensor_reliability": 0.1},
    )

    assert (
        stale["components"]["sensor_reliability"]["value"]
        == fresh["components"]["sensor_reliability"]["value"]
    )
    assert (
        stale["components"]["sensor_reliability"]["effective_weight"]
        < fresh["components"]["sensor_reliability"]["effective_weight"]
    )

    # Stale sensor evidence reduces overall coverage. The high score must
    # therefore be capped rather than presented as HIGH confidence.
    assert stale["evidence_coverage"] < K.ACI_MIN_COVERAGE_FOR_HIGH
    assert stale["aci"] == K.ACI_LOW_COVERAGE_CAP
    assert stale["capped"] is True


def test_mahalanobis_requires_sufficient_reference_history():
    rows = [
        dict(soil=40 + i, temperature=25 + i, humidity=60 + i)
        for i in range(4)
    ]

    result = mahalanobis_novelty(
        dict(soil=90, temperature=40, humidity=20),
        rows,
    )

    assert result["available"] is False


def test_mahalanobis_flags_multivariate_outlier():
    rows = [
        dict(
            soil=40 + (i % 3),
            temperature=25 + (i % 2),
            humidity=60 + (i % 4),
            rain=float(i % 2),
            water=1500 + 10 * (i % 3),
            light=400 + 5 * (i % 4),
        )
        for i in range(30)
    ]

    familiar = mahalanobis_novelty(rows[0], rows)

    unusual = mahalanobis_novelty(
        dict(
            soil=95,
            temperature=55,
            humidity=10,
            rain=90,
            water=100,
            light=5,
        ),
        rows,
    )

    assert familiar["available"] and unusual["available"]
    assert unusual["novelty"] > familiar["novelty"]
