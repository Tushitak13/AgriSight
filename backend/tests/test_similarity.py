"""Pure similarity-engine tests (no database)."""
from types import SimpleNamespace

import pytest

from app.services.similarity import similarity_engine as eng

BASE = {"soil": 35, "temperature": 30, "humidity": 65, "rain": 0, "water": 1700, "light": 450}


def test_identical_conditions_are_fully_similar():
    r = eng.compare(BASE, dict(BASE))
    assert r["similarity"] == 1.0 and r["distance"] == 0.0
    assert r["coverage"] == 1.0 and set(r["fields_compared"]) == set(BASE)


def test_similarity_decreases_as_soil_gap_grows():
    sims = [eng.compare(BASE, dict(BASE, soil=35 + d))["similarity"] for d in (0, 5, 15, 30)]
    assert sims == sorted(sims, reverse=True) and len(set(sims)) == 4


def test_compare_is_symmetric():
    other = dict(BASE, soil=50, temperature=22, light=2000)
    assert eng.compare(BASE, other)["similarity"] == eng.compare(other, BASE)["similarity"]


def test_difference_beyond_scale_is_capped_at_fully_different():
    r = eng.compare({"soil": 0, "temperature": 20}, {"soil": 100, "temperature": 20})
    assert r["field_distances"]["soil"] == 1.0
    assert 0.0 <= r["similarity"] <= 1.0


def test_soil_matters_more_than_humidity():
    # same normalised gap (0.5 of scale) in each; soil weight 0.30 > humidity weight 0.15
    soil_off = eng.compare(BASE, dict(BASE, soil=35 + 20))["similarity"]
    hum_off = eng.compare(BASE, dict(BASE, humidity=65 + 20))["similarity"]
    assert soil_off < hum_off


def test_light_is_compared_on_a_log_scale():
    near = eng.compare(BASE, dict(BASE, light=900))["similarity"]        # 2x brighter
    far = eng.compare(BASE, dict(BASE, light=45000))["similarity"]       # 100x brighter
    assert near > far
    assert eng.compare(BASE, dict(BASE, light=0))["field_distances"]["light"] <= 1.0   # zero lux is safe


def test_missing_fields_are_skipped_and_weights_renormalised():
    past = {"soil": 35, "temperature": 30, "humidity": 65}               # no rain/water/light
    r = eng.compare(BASE, past)
    assert r["similarity"] == 1.0                                        # shared fields all match
    assert set(r["fields_compared"]) == {"soil", "temperature", "humidity"}
    assert r["coverage"] == pytest.approx(0.65)


def test_too_little_overlap_is_not_comparable():
    assert eng.compare({"soil": 35, "light": 450}, {"rain": 0, "water": 1700}) is None
    assert eng.compare({"humidity": 60, "light": 450}, {"humidity": 60, "light": 450}) is None  # weight 0.25 < 0.4


def _exp(i, soil, status=None, intervention="light_irrigation", change=None):
    return SimpleNamespace(id=i, condition=dict(BASE, soil=soil), outcome_status=status,
                           intervention=intervention, soil_change=change)


def test_rank_orders_by_similarity_and_applies_k_and_cutoff():
    exps = [_exp(1, 60), _exp(2, 35), _exp(3, 38), _exp(4, 99)]
    ranked = eng.rank(BASE, exps, k=2, min_similarity=0.5)
    assert [e.id for e, _ in ranked] == [2, 3]
    all_ranked = eng.rank(BASE, exps, k=10, min_similarity=0.0)
    assert [e.id for e, _ in all_ranked][:3] == [2, 3, 1]
    assert 4 not in [e.id for e, _ in eng.rank(BASE, exps, k=10, min_similarity=0.9)]


def test_rank_ties_prefer_newer_experience():
    ranked = eng.rank(BASE, [_exp(1, 35), _exp(2, 35)], k=2, min_similarity=0.0)
    assert [e.id for e, _ in ranked] == [2, 1]


def test_historical_similarity_is_scaled_by_number_of_matches():
    one = eng.rank(BASE, [_exp(1, 35)], 5, 0.5)
    three = eng.rank(BASE, [_exp(i, 35) for i in (1, 2, 3)], 5, 0.5)
    assert eng.historical_similarity([]) == 0.0
    assert eng.historical_similarity(one) == pytest.approx(1 / 3, abs=1e-3)   # perfect but only 1 match
    assert eng.historical_similarity(three) == 1.0


def test_intervention_summary_is_similarity_weighted_and_skips_pending():
    exps = [_exp(1, 35, "SUCCESSFUL", "light_irrigation", 20.0),
            _exp(2, 35, "UNSUCCESSFUL", "light_irrigation", 2.0),
            _exp(3, 35, "SUCCESSFUL", "heavy_irrigation", 30.0),
            _exp(4, 35, None, "heavy_irrigation")]                      # pending: ignored
    summary = {s["intervention"]: s for s in eng.summarize_interventions(eng.rank(BASE, exps, 10, 0.0))}
    assert summary["light_irrigation"]["n"] == 2
    assert summary["light_irrigation"]["weighted_success"] == 0.5
    assert summary["light_irrigation"]["mean_soil_change"] == 11.0
    assert summary["heavy_irrigation"]["n"] == 1 and summary["heavy_irrigation"]["weighted_success"] == 1.0
    assert eng.summarize_interventions(eng.rank(BASE, exps, 10, 0.0))[0]["intervention"] == "heavy_irrigation"


def test_historical_similarity_is_discounted_when_comparison_was_partial():
    no_soil = {k: v for k, v in BASE.items() if k != "soil"}            # soil distrusted -> left out of query
    full = eng.rank(BASE, [_exp(i, 35) for i in (1, 2, 3)], 5, 0.5)
    part = eng.rank(no_soil, [_exp(i, 35) for i in (1, 2, 3)], 5, 0.5)
    assert part[0][1]["similarity"] == 1.0 and part[0][1]["coverage"] == pytest.approx(0.7)
    assert eng.historical_similarity(full) == 1.0
    assert eng.historical_similarity(part) == pytest.approx(0.7)
