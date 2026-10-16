"""CRI tests: pure scoring maths, then the API."""
import pytest

from app.services.resilience import cri as C
from app.utils import constants as K
from tests.test_aci import OTHER, jpg_bytes, make_exp, upload  # noqa: F401

IDEAL = dict(temperature=25, humidity=60, soil=55, rain=0, water=1700, light=5000)
POOR = dict(temperature=40, humidity=20, soil=10, rain=0, water=300, light=5000)


# ---------------- pure scoring
def test_ideal_reading_scores_one():
    assert C.reading_favourability(IDEAL) == 1.0


def test_favourability_is_a_weighted_mean_of_state_scores():
    # soil DRY .5, temp NORMAL 1, humidity NORMAL 1, rain NO_RAIN 1, water SUFFICIENT 1, light LOW .7
    v = dict(IDEAL, soil=37, light=450)
    assert C.reading_favourability(v) == pytest.approx(0.82)


def test_excluded_fields_are_ignored_and_weights_renormalised():
    v = dict(IDEAL, soil=5)                                        # soil CRITICALLY_DRY
    assert C.reading_favourability(v) < 0.8
    assert C.reading_favourability(v, exclude={"soil"}) == 1.0
    assert C.reading_favourability(v, exclude=set(K.SENSOR_FIELDS)) is None
    assert C.reading_favourability({}) is None


def test_stress_severity_is_dominated_by_the_worst_factor():
    assert C.stress_severity(IDEAL) == 0.0
    one_bad = C.stress_severity(dict(IDEAL, soil=10))              # distress .9 on one factor of six
    assert one_bad == pytest.approx(0.7 * 0.9 + 0.3 * 0.15)
    assert one_bad > 0.6                                           # a plain average would be only 0.15
    assert C.stress_severity(dict(IDEAL, soil=10), exclude={"soil"}) == 0.0


def test_visual_stress_raises_severity_scaled_by_image_reliability_and_never_lowers_it():
    assert C.stress_severity(IDEAL, vision_state="possible_stress", vision_reliability=1.0) == 0.6
    assert C.stress_severity(IDEAL, vision_state="possible_stress", vision_reliability=0.5) == pytest.approx(0.3)
    assert C.stress_severity(IDEAL, vision_state="no_vegetation_detected", vision_reliability=1.0) == 0.0
    bad = dict(IDEAL, soil=10)
    assert C.stress_severity(bad, vision_state="healthy_appearance", vision_reliability=1.0) \
        == C.stress_severity(bad)


def test_recent_response_favours_newest_outcomes():
    assert C.recent_response_score([]) is None
    assert C.recent_response_score(["SUCCESSFUL"]) == 1.0
    newest_ok = C.recent_response_score(["SUCCESSFUL", "UNSUCCESSFUL"])
    newest_bad = C.recent_response_score(["UNSUCCESSFUL", "SUCCESSFUL"])
    assert newest_ok == pytest.approx(1 / 1.7) and newest_bad == pytest.approx(0.7 / 1.7)
    assert newest_ok > newest_bad
    assert C.recent_response_score(["SUCCESSFUL"] + ["UNSUCCESSFUL"] * 20) \
        == C.recent_response_score(["SUCCESSFUL"] + ["UNSUCCESSFUL"] * 4)        # only newest 5 count
    assert C.recent_response_score(["PARTIALLY_SUCCESSFUL"]) == 0.5


def test_cri_is_the_weighted_mean_of_its_components():
    r = C.compute_cri(0.82, 0.25, 0.80, 0.76)                      # tolerance = 0.75
    assert r["cri"] == pytest.approx(0.783, abs=1e-3)              # .3*.82 + .3*.75 + .2*.80 + .2*.76
    assert r["cri_percent"] == pytest.approx(78.3, abs=0.1) and r["level"] == "HIGH"
    assert r["weakest_component"] == "stress_tolerance"
    assert r["data_support"] == dict(historical_recovery=True, recent_response=True)


def test_missing_recovery_history_uses_the_neutral_prior_and_is_flagged():
    r = C.compute_cri(1.0, 0.0, None, None)
    assert r["components"]["historical_recovery"]["value"] == K.CRI_NEUTRAL
    assert r["components"]["recent_response"]["value"] == K.CRI_NEUTRAL
    assert r["data_support"] == dict(historical_recovery=False, recent_response=False)
    assert r["cri"] == pytest.approx(0.8)                          # perfect conditions alone cannot reach 1.0
    assert C.compute_cri(1, 0, 1, 1)["cri"] == 1.0


def test_cri_levels_and_clamping():
    assert C.cri_level(K.CRI_HIGH) == "HIGH" and C.cri_level(K.CRI_HIGH - 0.001) == "MODERATE"
    assert C.cri_level(K.CRI_LOW) == "MODERATE" and C.cri_level(K.CRI_LOW - 0.001) == "LOW"
    r = C.compute_cri(5, -3, 2, -1)
    assert 0.0 <= r["cri"] <= 1.0


# ---------------- API
def post_readings(client, values, device_id="esp32-01", n=5):
    for _ in range(n):
        assert client.post("/api/sensors/readings", json=dict(values, device_id=device_id)).status_code == 201


def get_cri(client, device_id="esp32-01"):
    r = client.get(f"/api/cri/current?device_id={device_id}")
    assert r.status_code == 200
    return r.json()


def test_cri_404_without_readings(client):
    assert client.get("/api/cri/current").status_code == 404


def test_cri_good_conditions_beat_poor_conditions(client):
    post_readings(client, IDEAL, "good")
    post_readings(client, POOR, "poor")
    good, poor = get_cri(client, "good"), get_cri(client, "poor")
    assert good["components"]["environmental_stability"]["value"] == 1.0
    assert good["stress_severity"] == 0.0 and poor["stress_severity"] > 0.6
    assert good["cri"] > poor["cri"] + 0.2
    assert poor["weakest_component"] in ("stress_tolerance", "environmental_stability")
    assert good["cri_percent"] == pytest.approx(good["cri"] * 100, abs=0.1)


def test_cri_without_history_flags_neutral_prior(client):
    post_readings(client, IDEAL)
    d = get_cri(client)
    assert d["data_support"] == dict(historical_recovery=False, recent_response=False)
    assert d["components"]["historical_recovery"]["value"] == 0.5
    assert d["components"]["recent_response"]["value"] == 0.5
    assert d["cri"] == pytest.approx(0.8) and d["level"] == "HIGH"
    assert d["n_similar_with_outcome"] == 0


def test_cri_learns_from_similar_past_outcomes(client):
    for dev, status in (("wins", "SUCCESSFUL"), ("fails", "UNSUCCESSFUL")):
        post_readings(client, IDEAL, dev)
        for _ in range(3):
            make_exp(client, IDEAL, status, device_id=dev)
    wins, fails = get_cri(client, "wins"), get_cri(client, "fails")
    assert wins["components"]["historical_recovery"]["value"] == 1.0
    assert fails["components"]["historical_recovery"]["value"] == 0.0
    assert wins["data_support"]["historical_recovery"] is True and wins["n_similar_with_outcome"] == 3
    assert wins["cri"] > fails["cri"] + 0.3


def test_cri_ignores_outcomes_of_unrelated_conditions_for_historical_recovery(client):
    post_readings(client, IDEAL)
    for _ in range(3):
        make_exp(client, OTHER, "UNSUCCESSFUL")
    d = get_cri(client)
    assert d["data_support"]["historical_recovery"] is False          # nothing similar
    assert d["data_support"]["recent_response"] is True               # but recent response still counts
    assert d["components"]["recent_response"]["value"] == 0.0


def test_cri_recent_response_weights_newest_outcome_most(client):
    for dev, order in (("improving", ["UNSUCCESSFUL", "UNSUCCESSFUL", "SUCCESSFUL"]),
                       ("declining", ["SUCCESSFUL", "UNSUCCESSFUL", "UNSUCCESSFUL"])):     # oldest -> newest
        post_readings(client, IDEAL, dev)
        for status in order:
            make_exp(client, OTHER, status, device_id=dev)
    up, down = get_cri(client, "improving"), get_cri(client, "declining")
    assert up["components"]["recent_response"]["value"] == pytest.approx(1 / 2.19, abs=1e-3)
    assert down["components"]["recent_response"]["value"] == pytest.approx(0.49 / 2.19, abs=1e-3)
    assert up["cri"] > down["cri"]


def test_cri_uses_trusted_visual_stress(client):
    post_readings(client, IDEAL)
    base = get_cri(client)
    assert base["vision_used"] is False and base["stress_severity"] == 0.0
    upload(client, "healthy")
    healthy = get_cri(client)
    assert healthy["vision_used"] is True and healthy["stress_severity"] == 0.0
    upload(client, "stressed")
    stressed = get_cri(client)
    assert stressed["stress_severity"] > 0.5
    assert stressed["cri"] < healthy["cri"]


def test_cri_ignores_untrusted_image(client):
    post_readings(client, IDEAL)
    client.post("/api/vision/analyze", files={"file": ("b.jpg", jpg_bytes("blurry"), "image/jpeg")})
    d = get_cri(client)
    assert d["vision_used"] is False and d["stress_severity"] == 0.0


def test_cri_replaces_anomalous_sensor_with_last_known_good(client):
    for soil in (55, 56, 54, 55, 56, 55, 54, 55, 56, 55):
        client.post("/api/sensors/readings", json=dict(IDEAL, soil=soil))
    steady = get_cri(client)
    client.post("/api/sensors/readings", json=dict(IDEAL, soil=5))      # spike to 'critically dry'
    d = get_cri(client)
    assert d["substituted_fields"] == ["soil"] and d["excluded_fields"] == []
    assert d["stress_severity"] == steady["stress_severity"] == 0.0     # the fake drought is not believed


def test_distrusting_a_sensor_never_makes_the_crop_look_healthier(client):
    dry = dict(IDEAL, soil=35)                                          # genuinely DRY (distress 0.5)
    for _ in range(10):
        client.post("/api/sensors/readings", json=dry)
    before = get_cri(client)
    assert before["stress_severity"] > 0.3
    client.post("/api/sensors/readings", json=dict(dry, soil=95))       # spike: soil now distrusted
    after = get_cri(client)
    assert after["substituted_fields"] == ["soil"]
    assert after["stress_severity"] == pytest.approx(before["stress_severity"])
    assert after["cri"] == pytest.approx(before["cri"], abs=0.02)


def test_sensor_with_no_valid_history_is_excluded(client):
    client.post("/api/sensors/readings", json=dict(IDEAL, soil=150))    # out of range, first ever reading
    d = get_cri(client)
    assert d["excluded_fields"] == ["soil"] and d["substituted_fields"] == []
