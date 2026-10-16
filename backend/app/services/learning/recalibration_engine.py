
"""Safe, offline recalibration candidates for soil-change predictions.

This module never changes active models, recommendations, or hardware.
Only explicitly ROLA-eligible examples may be used.
"""

from math import isfinite
from statistics import mean
from typing import Any, Mapping, Sequence


def _value(record: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a dictionary or an ORM-like object."""
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _eligible_examples(records: Sequence[Any]) -> list[dict]:
    """Keep only real, completed, finite, explicitly eligible examples."""
    eligible = []

    for record in records:
        if _value(record, "source") != "real":
            continue
        if _value(record, "outcome_status") is None:
            continue
        if _value(record, "attribution_eligible") is not True:
            continue

        predicted = _value(record, "expected_soil_change")
        observed = _value(record, "soil_change")

        if isinstance(predicted, bool) or isinstance(observed, bool):
            continue
        if not isinstance(predicted, (int, float)):
            continue
        if not isinstance(observed, (int, float)):
            continue
        if not isfinite(predicted) or not isfinite(observed):
            continue

        eligible.append({
            "predicted": float(predicted),
            "observed": float(observed),
            "error": float(observed) - float(predicted),
        })

    return eligible


def generate_candidate(
    training_records: Sequence[Any],
    *,
    min_training_samples: int = 10,
) -> dict:
    """Estimate an additive correction using training records only.

    corrected prediction = original prediction + correction

    The correction is the mean observed-minus-predicted error.
    The candidate is NOT deployed by this function.
    """
    if min_training_samples < 2:
        raise ValueError("min_training_samples must be at least 2")

    examples = _eligible_examples(training_records)

    if len(examples) < min_training_samples:
        return {
            "status": "INSUFFICIENT_TRAINING_DATA",
            "training_samples": len(examples),
            "required_training_samples": min_training_samples,
            "correction": None,
        }

    errors = [item["error"] for item in examples]
    correction = mean(errors)

    return {
        "status": "PENDING_VALIDATION",
        "method": "mean_additive_bias_correction",
        "training_samples": len(examples),
        "correction": correction,
        "training_mae_before": mean(
            abs(item["predicted"] - item["observed"])
            for item in examples
        ),
        "training_mae_after": mean(
            abs(item["predicted"] + correction - item["observed"])
            for item in examples
        ),
        "active_model_modified": False,
    }


def validate_candidate(
    candidate: Mapping[str, Any],
    holdout_records: Sequence[Any],
    *,
    min_holdout_samples: int = 5,
    min_relative_improvement: float = 0.05,
) -> dict:
    """Evaluate a candidate on separate, ROLA-eligible holdout records."""
    if min_holdout_samples < 1:
        raise ValueError("min_holdout_samples must be at least 1")
    if not 0 <= min_relative_improvement < 1:
        raise ValueError("min_relative_improvement must be in [0, 1)")

    if candidate.get("status") != "PENDING_VALIDATION":
        return {
            "status": "REJECTED",
            "reason": "Candidate is not pending validation",
            "active_model_modified": False,
        }

    correction = candidate.get("correction")
    if (
        isinstance(correction, bool)
        or not isinstance(correction, (int, float))
        or not isfinite(correction)
    ):
        return {
            "status": "REJECTED",
            "reason": "Candidate correction is invalid",
            "active_model_modified": False,
        }

    examples = _eligible_examples(holdout_records)

    if len(examples) < min_holdout_samples:
        return {
            "status": "INSUFFICIENT_HOLDOUT_DATA",
            "holdout_samples": len(examples),
            "required_holdout_samples": min_holdout_samples,
            "active_model_modified": False,
        }

    baseline_mae = mean(
        abs(item["predicted"] - item["observed"])
        for item in examples
    )
    candidate_mae = mean(
        abs(item["predicted"] + correction - item["observed"])
        for item in examples
    )

    if baseline_mae == 0:
        relative_improvement = 0.0
    else:
        relative_improvement = (baseline_mae - candidate_mae) / baseline_mae

    passed = (
        candidate_mae < baseline_mae
        and relative_improvement >= min_relative_improvement
    )

    return {
        "status": "VALIDATED" if passed else "REJECTED",
        "reason": (
            "Holdout improvement met the configured threshold"
            if passed
            else "Holdout improvement did not meet the configured threshold"
        ),
        "holdout_samples": len(examples),
        "baseline_mae": baseline_mae,
        "candidate_mae": candidate_mae,
        "relative_improvement": relative_improvement,
        "minimum_relative_improvement": min_relative_improvement,
        "active_model_modified": False,
        "deployment_approval_required": True,
    }
