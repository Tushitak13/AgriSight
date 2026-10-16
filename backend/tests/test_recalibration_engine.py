
import pytest

from app.services.learning.recalibration_engine import (
    generate_candidate,
    validate_candidate,
)


def make_record(predicted, observed, *, source="real", eligible=True):
    return {
        "source": source,
        "outcome_status": "RECORDED",
        "expected_soil_change": predicted,
        "soil_change": observed,
        "attribution_eligible": eligible,
    }


def test_insufficient_training_data():
    records = [make_record(5, 7) for _ in range(3)]

    result = generate_candidate(records, min_training_samples=5)

    assert result["status"] == "INSUFFICIENT_TRAINING_DATA"
    assert result["correction"] is None


def test_seed_and_ineligible_records_are_excluded():
    records = (
        [make_record(5, 7) for _ in range(4)]
        + [make_record(5, 7, source="seed") for _ in range(10)]
        + [make_record(5, 7, eligible=False) for _ in range(10)]
    )

    result = generate_candidate(records, min_training_samples=5)

    assert result["status"] == "INSUFFICIENT_TRAINING_DATA"
    assert result["training_samples"] == 4


def test_candidate_estimates_additive_bias():
    records = [make_record(5, 7) for _ in range(10)]

    candidate = generate_candidate(records, min_training_samples=10)

    assert candidate["status"] == "PENDING_VALIDATION"
    assert candidate["correction"] == pytest.approx(2.0)
    assert candidate["active_model_modified"] is False


def test_candidate_passes_when_holdout_error_improves():
    training = [make_record(5, 7) for _ in range(10)]
    holdout = [make_record(10, 12) for _ in range(5)]

    candidate = generate_candidate(training, min_training_samples=10)
    result = validate_candidate(
        candidate,
        holdout,
        min_holdout_samples=5,
        min_relative_improvement=0.05,
    )

    assert result["status"] == "VALIDATED"
    assert result["baseline_mae"] == pytest.approx(2.0)
    assert result["candidate_mae"] == pytest.approx(0.0)
    assert result["deployment_approval_required"] is True
    assert result["active_model_modified"] is False


def test_candidate_rejected_when_holdout_error_worsens():
    training = [make_record(5, 7) for _ in range(10)]
    holdout = [make_record(10, 9) for _ in range(5)]

    candidate = generate_candidate(training, min_training_samples=10)
    result = validate_candidate(candidate, holdout)

    assert result["status"] == "REJECTED"
    assert result["candidate_mae"] > result["baseline_mae"]


def test_insufficient_holdout_data_does_not_validate():
    candidate = generate_candidate(
        [make_record(5, 7) for _ in range(10)],
        min_training_samples=10,
    )

    result = validate_candidate(
        candidate,
        [make_record(5, 7) for _ in range(2)],
        min_holdout_samples=5,
    )

    assert result["status"] == "INSUFFICIENT_HOLDOUT_DATA"
    assert result["active_model_modified"] is False


def test_missing_or_nonfinite_values_are_excluded():
    records = [
        make_record(5, 7),
        make_record(None, 7),
        make_record(5, None),
        make_record(float("nan"), 7),
        make_record(5, float("inf")),
    ]

    result = generate_candidate(records, min_training_samples=2)

    assert result["status"] == "INSUFFICIENT_TRAINING_DATA"
    assert result["training_samples"] == 1


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError):
        generate_candidate([], min_training_samples=1)

    with pytest.raises(ValueError):
        validate_candidate(
            {"status": "PENDING_VALIDATION", "correction": 1.0},
            [],
            min_relative_improvement=1.0,
        )
