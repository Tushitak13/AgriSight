from app.services.learning.flai_engine import decide, reliability_adjusted_probability, calculate_net_voi, recovery_check
import pytest
from pydantic import ValidationError
from app.schemas.flai_schema import RecoveryInput

BASE={
 "prior_threat_probability":0.2,
 "evidence":[{"name":"fresh_sensor","likelihood_ratio":4.0,"quality":0.9,"freshness":1.0,"validity":1.0}],
 "risk_limit":0.1,"cvar_weight":0.5,"cvar_alpha":0.9,
 "actions":[
  {"action_type":"MONITOR","expected_recovery_benefit":1,"action_cost":0.1,"resource_cost":0,"side_effect_cost":0,"serious_harm_probability":0.01,"serious_harm_loss":10,"loss_samples":[0,0,1],"feasible":True,"supported_by_evidence":True},
  {"action_type":"TREAT","expected_recovery_benefit":8,"action_cost":1,"resource_cost":1,"side_effect_cost":1,"serious_harm_probability":0.2,"serious_harm_loss":100,"loss_samples":[0,10,100],"feasible":True,"supported_by_evidence":True},
 ]
}

def test_unreliable_evidence_moves_probability_less():
    high,_=reliability_adjusted_probability(0.2,[{"name":"e","likelihood_ratio":5,"quality":1,"freshness":1,"validity":1}])
    low,_=reliability_adjusted_probability(0.2,[{"name":"e","likelihood_ratio":5,"quality":0.1,"freshness":1,"validity":1}])
    assert high > low > 0.2

def test_unsafe_action_is_rejected():
    out=decide(BASE)
    assert out["selected_action"] == "MONITOR"
    assert any(x["action"]=="TREAT" for x in out["rejected_actions"])
    assert out["actuation_enabled"] is False

def test_net_voi_includes_costs_and_waiting_safety():
    out=calculate_net_voi({"provided":True,"expected_best_utility_after_observation":10,"current_best_utility":6,"measurement_cost":1,"delay_cost":1,"waiting_safe":True})
    assert out["net_voi"] == 2
    assert out["collect_information"] is True
    unsafe=calculate_net_voi({"provided":True,"expected_best_utility_after_observation":100,"current_best_utility":0,"measurement_cost":0,"delay_cost":0,"waiting_safe":False})
    assert unsafe["collect_information"] is False

def test_recovery_trigger_requires_valid_evidence_and_appropriate_timing():
    out=recovery_check({"provided":True,"observed_value":8,"expected_value":2,"observed_variance":1,"expected_variance":1,"z_threshold":2,"evidence_valid":True,"timing_appropriate":True})
    assert out["reassessment_required"] is True
    invalid=recovery_check({"provided":True,"observed_value":8,"expected_value":2,"observed_variance":1,"expected_variance":1,"z_threshold":2,"evidence_valid":False,"timing_appropriate":True})
    assert invalid["reassessment_required"] is False

def test_no_safe_candidate_escalates():
    req={"prior_threat_probability":0.5,"evidence":[],"risk_limit":0.01,"cvar_weight":1,"cvar_alpha":0.95,"actions":[{"action_type":"TREAT","expected_recovery_benefit":10,"action_cost":0,"resource_cost":0,"side_effect_cost":0,"serious_harm_probability":0.5,"serious_harm_loss":100,"loss_samples":[],"feasible":True,"supported_by_evidence":True}]}
    assert decide(req)["selected_action"] == "ESCALATE"
def test_positive_voi_does_not_override_better_action():
    req = {
        "prior_threat_probability": 0.2,
        "evidence": [],
        "risk_limit": 0.1,
        "cvar_weight": 0,
        "cvar_alpha": 0.95,
        "actions": [
            {
                "action_type": "MONITOR",
                "expected_recovery_benefit": 5,
                "action_cost": 0,
                "resource_cost": 0,
                "side_effect_cost": 0,
                "serious_harm_probability": 0.01,
                "serious_harm_loss": 10,
                "loss_samples": [],
                "feasible": True,
                "supported_by_evidence": True,
            },
            {
                "action_type": "VERIFY",
                "expected_recovery_benefit": 2,
                "action_cost": 0,
                "resource_cost": 0,
                "side_effect_cost": 0,
                "serious_harm_probability": 0.01,
                "serious_harm_loss": 10,
                "loss_samples": [],
                "feasible": True,
                "supported_by_evidence": True,
            },
        ],
        "voi": {
            "provided": True,
            "expected_best_utility_after_observation": 10,
            "current_best_utility": 5,
            "measurement_cost": 1,
            "delay_cost": 1,
            "waiting_safe": True,
        },
    }

    out = decide(req)

    assert out["net_voi"]["collect_information"] is True
    assert out["selected_action"] == "MONITOR"
    assert out["net_voi"]["verification_selected"] is False

def test_recovery_check_rejects_non_finite_observed_value():
    for value in (float("nan"), float("inf"), float("-inf")):
        out = recovery_check({
            "provided": True,
            "observed_value": value,
            "expected_value": 2.0,
            "observed_variance": 1.0,
            "expected_variance": 1.0,
            "z_threshold": 2.0,
            "evidence_valid": True,
            "timing_appropriate": True,
        })

        assert out["reassessment_required"] is False
        assert out["z_score"] is None


def test_recovery_check_rejects_non_finite_variance():
    for variance in (float("nan"), float("inf"), float("-inf")):
        out = recovery_check({
            "provided": True,
            "observed_value": 8.0,
            "expected_value": 2.0,
            "observed_variance": variance,
            "expected_variance": 1.0,
            "z_threshold": 2.0,
            "evidence_valid": True,
            "timing_appropriate": True,
        })

        assert out["reassessment_required"] is False
        assert out["z_score"] is None



def test_recovery_schema_rejects_non_finite_numeric_values():
    numeric_fields = [
        "observed_value",
        "expected_value",
        "observed_variance",
        "expected_variance",
        "z_threshold",
    ]

    for field in numeric_fields:
        for value in (float("nan"), float("inf"), float("-inf")):
            payload = {
                "observed_value": 8.0,
                "expected_value": 2.0,
                "observed_variance": 1.0,
                "expected_variance": 1.0,
                "z_threshold": 2.0,
                "evidence_valid": True,
                "timing_appropriate": True,
            }
            payload[field] = value

            with pytest.raises(ValidationError):
                RecoveryInput(**payload)

def test_recovery_discrepancy_recommends_separate_rola_assessment():
    request = {
        "prior_threat_probability": 0.2,
        "evidence": [],
        "risk_limit": 0.1,
        "cvar_weight": 0.5,
        "cvar_alpha": 0.9,
        "actions": [
            {
                "action_type": "MONITOR",
                "expected_recovery_benefit": 1,
                "action_cost": 0.1,
                "resource_cost": 0,
                "side_effect_cost": 0,
                "serious_harm_probability": 0.01,
                "serious_harm_loss": 10,
                "feasible": True,
                "supported_by_evidence": True,
            }
        ],
        "recovery": {
            "provided": True,
            "observed_value": 8.0,
            "expected_value": 2.0,
            "observed_variance": 1.0,
            "expected_variance": 1.0,
            "z_threshold": 2.0,
            "evidence_valid": True,
            "timing_appropriate": True,
        },
    }

    result = decide(request)

    assert result["reassessment_required"] is True
    assert result["rola_assessment_recommended"] is True
    assert result["actuation_enabled"] is False
    assert result["selected_action"] == "MONITOR"


def test_no_recovery_discrepancy_does_not_recommend_rola():
    request = {
        "prior_threat_probability": 0.2,
        "evidence": [],
        "risk_limit": 0.1,
        "cvar_weight": 0.5,
        "cvar_alpha": 0.9,
        "actions": [
            {
                "action_type": "MONITOR",
                "expected_recovery_benefit": 1,
                "action_cost": 0.1,
                "resource_cost": 0,
                "side_effect_cost": 0,
                "serious_harm_probability": 0.01,
                "serious_harm_loss": 10,
                "feasible": True,
                "supported_by_evidence": True,
            }
        ],
        "recovery": {
            "provided": True,
            "observed_value": 2.1,
            "expected_value": 2.0,
            "observed_variance": 1.0,
            "expected_variance": 1.0,
            "z_threshold": 2.0,
            "evidence_valid": True,
            "timing_appropriate": True,
        },
    }

    result = decide(request)

    assert result["reassessment_required"] is False
    assert result["rola_assessment_recommended"] is False
    assert result["actuation_enabled"] is False
