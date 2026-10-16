"""ROLA v1: conservative response assessment, with recalibration intentionally disabled.

This module is pure Python and does not modify ACI, sensor reliability, or intervention
recommendations. It assesses whether a predicted numeric response can be compared with
an observation, computes an error when valid, and reports evidence limitations.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

VALID_SOURCE_TYPES = {"manual_observation", "reference_measurement", "operational_sensor"}
VALID_VALUE_KINDS = {"numeric_measurement", "qualitative_assessment"}


def _parse_timestamp(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def assess_response(
    *,
    predicted_value: float | int | None,
    predicted_unit: str | None,
    predicted_at: datetime | str | None,
    observed_value: float | int | None,
    observed_unit: str | None,
    observed_at: datetime | str | None,
    source_type: str,
    value_kind: str = "numeric_measurement",
    independent_of_target_sensor: bool = False,
    predicted_depth_cm: float | None = None,
    observed_depth_cm: float | None = None,
    event_recorded: bool = True,
    event_timing_trustworthy: bool = True,
    model_calibrated_for_context: bool = False,
    observation_quality_ok: bool = True,
    max_observation_age_hours: float = 72.0,
) -> dict:
    """Assess one predicted-vs-observed response without learning or changing weights.

    A numeric error is computed only when units, measurement depth, timestamps, values,
    and observation quality are comparable. A same-device operational sensor can provide
    a monitoring error but is not independent verification and cannot support sensor-fault
    attribution on its own.
    """
    reasons: list[str] = []
    source_type = str(source_type)
    value_kind = str(value_kind)
    p_time = _parse_timestamp(predicted_at)
    o_time = _parse_timestamp(observed_at)

    if source_type not in VALID_SOURCE_TYPES:
        reasons.append("unknown_source_type")
    if value_kind not in VALID_VALUE_KINDS:
        reasons.append("unknown_value_kind")
    if value_kind == "qualitative_assessment":
        reasons.append("qualitative_observation_not_numerically_comparable")
    if not _finite_number(predicted_value):
        reasons.append("invalid_or_missing_prediction")
    if not _finite_number(observed_value):
        reasons.append("invalid_or_missing_observation")
    if not predicted_unit or not observed_unit or predicted_unit.strip().lower() != observed_unit.strip().lower():
        reasons.append("unit_mismatch")
    if p_time is None:
        reasons.append("invalid_or_missing_prediction_timestamp")
    if o_time is None:
        reasons.append("invalid_or_missing_observation_timestamp")
    if p_time is not None and o_time is not None and o_time < p_time:
        reasons.append("observation_precedes_prediction")
    if p_time is not None and o_time is not None and o_time >= p_time:
        age = (o_time - p_time).total_seconds() / 3600.0
        if age > max_observation_age_hours:
            reasons.append("observation_outside_evaluation_window")
    if predicted_depth_cm is None or observed_depth_cm is None:
        reasons.append("measurement_depth_unspecified")
    elif not (_finite_number(predicted_depth_cm) and _finite_number(observed_depth_cm)):
        reasons.append("invalid_measurement_depth")
    elif abs(float(predicted_depth_cm) - float(observed_depth_cm)) > 1e-6:
        reasons.append("measurement_depth_mismatch")
    if not event_recorded:
        reasons.append("event_not_verified_or_missing")
    if not event_timing_trustworthy:
        reasons.append("event_timing_uncertain")
    if not observation_quality_ok:
        reasons.append("observation_quality_failed")

    hard_comparison_failures = {
        "unknown_source_type", "unknown_value_kind", "qualitative_observation_not_numerically_comparable",
        "invalid_or_missing_prediction", "invalid_or_missing_observation", "unit_mismatch",
        "invalid_or_missing_prediction_timestamp", "invalid_or_missing_observation_timestamp",
        "observation_precedes_prediction", "observation_outside_evaluation_window",
        "measurement_depth_unspecified", "invalid_measurement_depth", "measurement_depth_mismatch",
        "observation_quality_failed",
    }
    comparable = not any(r in hard_comparison_failures for r in reasons)
    signed_error = (float(observed_value) - float(predicted_value)) if comparable else None
    absolute_error = abs(signed_error) if signed_error is not None else None

    independent = source_type in {"manual_observation", "reference_measurement"} and bool(independent_of_target_sensor)
    attribution_eligible = bool(
        comparable and independent and event_recorded and event_timing_trustworthy
        and model_calibrated_for_context
    )
    if source_type == "operational_sensor" or not independent:
        reasons.append("independent_verification_unavailable")
    if not model_calibrated_for_context:
        reasons.append("model_not_verified_for_context")
    if not event_recorded or not event_timing_trustworthy:
        attribution = "INSUFFICIENT_EVIDENCE"
    elif not comparable:
        attribution = "NOT_COMPARABLE"
    elif not independent:
        attribution = "UNVERIFIED_RESPONSE_ERROR" if absolute_error is not None else "INSUFFICIENT_EVIDENCE"
    elif not model_calibrated_for_context:
        attribution = "MODEL_CONTEXT_UNVERIFIED"
    else:
        # Deliberately no automatic sensor-vs-model diagnosis from one sample.
        attribution = "REVIEW_REQUIRED"

    return {
        "comparable": comparable,
        "signed_error": round(signed_error, 6) if signed_error is not None else None,
        "absolute_error": round(absolute_error, 6) if absolute_error is not None else None,
        "source_type": source_type,
        "independent_verification": independent,
        "attribution_eligible": attribution_eligible,
        "attribution": attribution,
        "reasons": list(dict.fromkeys(reasons)),
        "recalibration_applied": False,
        "recommendation_or_aci_modified": False,
    }


def summarize_error_history(errors: list[float | int | None]) -> dict:
    """Summarize valid numeric errors for diagnostics only; no EWMA/update is applied."""
    valid = [abs(float(e)) for e in errors if _finite_number(e)]
    if not valid:
        return {"count": 0, "mean_absolute_error": None, "max_absolute_error": None}
    return {
        "count": len(valid),
        "mean_absolute_error": round(sum(valid) / len(valid), 6),
        "max_absolute_error": round(max(valid), 6),
    }
