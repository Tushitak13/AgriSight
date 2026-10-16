from datetime import datetime, timedelta, timezone
import pytest

from app.services.learning.rola_engine import assess_response, summarize_error_history

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def assess(**overrides):
    args = dict(
        predicted_value=40.0, predicted_unit="%VWC", predicted_at=NOW - timedelta(hours=2),
        observed_value=34.0, observed_unit="%VWC", observed_at=NOW,
        source_type="reference_measurement", value_kind="numeric_measurement",
        independent_of_target_sensor=True, predicted_depth_cm=10.0, observed_depth_cm=10.0,
        event_recorded=True, event_timing_trustworthy=True, model_calibrated_for_context=True,
        observation_quality_ok=True,
    )
    args.update(overrides)
    return assess_response(**args)


def test_comparable_independent_measurement_calculates_error_but_does_not_recalibrate():
    result = assess()
    assert result["comparable"] is True
    assert result["signed_error"] == -6.0
    assert result["absolute_error"] == 6.0
    assert result["independent_verification"] is True
    assert result["attribution_eligible"] is True
    assert result["attribution"] == "REVIEW_REQUIRED"
    assert result["recalibration_applied"] is False
    assert result["recommendation_or_aci_modified"] is False


def test_unit_mismatch_blocks_error_calculation():
    result = assess(observed_unit="kPa")
    assert result["comparable"] is False
    assert result["signed_error"] is None
    assert "unit_mismatch" in result["reasons"]


def test_depth_mismatch_blocks_error_calculation():
    result = assess(observed_depth_cm=20.0)
    assert result["comparable"] is False
    assert "measurement_depth_mismatch" in result["reasons"]


def test_missing_depth_blocks_error_calculation():
    result = assess(predicted_depth_cm=None)
    assert result["comparable"] is False
    assert "measurement_depth_unspecified" in result["reasons"]


def test_qualitative_manual_observation_is_stored_as_non_numeric_evidence():
    result = assess(source_type="manual_observation", value_kind="qualitative_assessment",
                    observed_value=None)
    assert result["comparable"] is False
    assert result["absolute_error"] is None
    assert "qualitative_observation_not_numerically_comparable" in result["reasons"]


def test_operational_sensor_error_is_not_independent_verification():
    result = assess(source_type="operational_sensor", independent_of_target_sensor=False)
    assert result["comparable"] is True
    assert result["absolute_error"] == 6.0
    assert result["independent_verification"] is False
    assert result["attribution_eligible"] is False
    assert result["attribution"] == "UNVERIFIED_RESPONSE_ERROR"


def test_untrusted_event_timing_prevents_attribution():
    result = assess(event_timing_trustworthy=False)
    assert result["attribution_eligible"] is False
    assert result["attribution"] == "INSUFFICIENT_EVIDENCE"


def test_unverified_model_context_prevents_attribution():
    result = assess(model_calibrated_for_context=False)
    assert result["attribution_eligible"] is False
    assert result["attribution"] == "MODEL_CONTEXT_UNVERIFIED"


def test_stale_observation_is_not_compared():
    result = assess(observed_at=NOW + timedelta(days=5))
    assert result["comparable"] is False
    assert "observation_outside_evaluation_window" in result["reasons"]


def test_observation_before_prediction_is_rejected():
    result = assess(observed_at=NOW - timedelta(hours=3))
    assert result["comparable"] is False
    assert "observation_precedes_prediction" in result["reasons"]


def test_bad_numeric_values_are_rejected():
    result = assess(observed_value=float("nan"))
    assert result["comparable"] is False
    assert result["absolute_error"] is None


def test_missing_event_record_prevents_attribution():
    result = assess(event_recorded=False)
    assert result["attribution_eligible"] is False
    assert result["attribution"] == "INSUFFICIENT_EVIDENCE"


def test_error_history_summary_ignores_missing_and_nonfinite_values():
    result = summarize_error_history([-2, 4, None, float("nan")])
    assert result == {"count": 2, "mean_absolute_error": 3.0, "max_absolute_error": 4.0}


def test_empty_error_history_has_no_fake_zero_score():
    assert summarize_error_history([None]) == {
        "count": 0, "mean_absolute_error": None, "max_absolute_error": None
    }
