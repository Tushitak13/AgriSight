"""AgriSight FLAI: recommendation-only constrained decision engine.

All utilities, likelihood ratios, safety limits, and outcome estimates must be
calibrated for the crop/threat by domain experts before field use.
"""
from __future__ import annotations
import math
from typing import Any

EPS = 1e-9

def clamp(x: float, low: float, high: float) -> float:
    return max(low, min(high, x))

def reliability_adjusted_probability(prior: float, evidence: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    """Reliability-tempered odds update. Likelihood ratios must be calibrated.

    Assumes conditionally independent evidence. Correlated sources can produce
    overconfidence; callers should combine correlated evidence upstream.
    """
    p = clamp(float(prior), EPS, 1.0-EPS)
    log_odds = math.log(p / (1.0-p))
    details=[]
    for item in evidence:
        lr=float(item['likelihood_ratio'])
        if lr <= 0:
            raise ValueError(f"likelihood_ratio for {item.get('name','evidence')} must be > 0")
        reliability = clamp(float(item['quality']),0,1) * clamp(float(item['freshness']),0,1) * clamp(float(item['validity']),0,1)
        contribution = reliability * math.log(lr)
        log_odds += contribution
        details.append({"name": item.get("name", "evidence"), "reliability": round(reliability, 6), "log_odds_contribution": round(contribution, 6)})
    # Stable logistic transform
    if log_odds >= 0:
        p=1.0/(1.0+math.exp(-min(log_odds, 700)))
    else:
        ex=math.exp(max(log_odds, -700)); p=ex/(1.0+ex)
    return clamp(p,0,1), details

def cvar_tail_loss(loss_samples: list[float], alpha: float) -> float:
    """Mean of the worst (1-alpha) fraction of sampled losses."""
    if not loss_samples:
        return 0.0
    alpha=clamp(alpha,0.0,0.999999)
    ordered=sorted((max(0.0,float(x)) for x in loss_samples), reverse=True)
    n=max(1, math.ceil((1.0-alpha)*len(ordered)))
    return sum(ordered[:n])/n

def action_utility(action: dict[str, Any], cvar_weight: float, cvar_alpha: float) -> tuple[float, float, str]:
    benefit=float(action['expected_recovery_benefit'])
    costs=float(action['action_cost'])+float(action['resource_cost'])+float(action['side_effect_cost'])
    samples=action.get('loss_samples') or []
    if samples:
        tail_loss=cvar_tail_loss(samples,cvar_alpha)
        loss_method="sampled_cvar"
    else:
        # Explicit proxy only: this is not a statistical CVaR estimate.
        tail_loss=float(action['serious_harm_probability'])*float(action['serious_harm_loss'])
        loss_method="harm_probability_loss_proxy"
    return benefit-costs-cvar_weight*tail_loss, tail_loss, loss_method


def recovery_check(recovery: dict[str, Any] | None) -> dict[str, Any]:
    if not recovery or not recovery.get("provided", False):
        return {
            "evaluated": False,
            "reassessment_required": False,
            "z_score": None,
            "reason": "No recovery observation supplied.",
        }

    if (
        not recovery.get("evidence_valid", False)
        or not recovery.get("timing_appropriate", False)
    ):
        return {
            "evaluated": True,
            "reassessment_required": False,
            "z_score": None,
            "reason": "Recovery observation is invalid or timing is not appropriate.",
        }

    try:
        observed_value = float(recovery["observed_value"])
        expected_value = float(recovery["expected_value"])
        observed_variance = float(recovery["observed_variance"])
        expected_variance = float(recovery["expected_variance"])
        z_threshold = float(recovery["z_threshold"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return {
            "evaluated": True,
            "reassessment_required": False,
            "z_score": None,
            "reason": "Recovery inputs are missing or invalid numeric values.",
        }

    numeric_values = (
        observed_value,
        expected_value,
        observed_variance,
        expected_variance,
        z_threshold,
    )

    if not all(math.isfinite(value) for value in numeric_values):
        return {
            "evaluated": True,
            "reassessment_required": False,
            "z_score": None,
            "reason": "Recovery inputs must all be finite numeric values.",
        }

    if observed_variance < 0 or expected_variance < 0 or z_threshold <= 0:
        return {
            "evaluated": True,
            "reassessment_required": False,
            "z_score": None,
            "reason": "Variances must be non-negative and the z-threshold must be positive.",
        }

    variance = observed_variance + expected_variance

    if not math.isfinite(variance) or variance <= 0:
        return {
            "evaluated": True,
            "reassessment_required": False,
            "z_score": None,
            "reason": "Combined measurement/prediction variance must be finite and positive.",
        }

    z = (observed_value - expected_value) / math.sqrt(variance)

    if not math.isfinite(z):
        return {
            "evaluated": True,
            "reassessment_required": False,
            "z_score": None,
            "reason": "Recovery discrepancy could not be calculated as a finite value.",
        }

    required = abs(z) > z_threshold

    return {
        "evaluated": True,
        "reassessment_required": required,
        "z_score": round(z, 6),
        "reason": (
            "Observed recovery differs materially from expected recovery."
            if required
            else "Recovery discrepancy is within the configured threshold."
        ),
    }


def calculate_net_voi(voi: dict[str, Any] | None) -> dict[str, Any]:
    if not voi or not voi.get('provided',False):
        return {"evaluated":False,"net_voi":None,"collect_information":False,"reason":"No Value-of-Information estimate supplied."}
    net=float(voi['expected_best_utility_after_observation'])-float(voi['current_best_utility'])-float(voi['measurement_cost'])-float(voi['delay_cost'])
    safe=bool(voi['waiting_safe'])
    collect=net>0 and safe
    if not safe: reason="Waiting is not considered safe; do not delay an urgent decision for information."
    elif collect: reason="Expected decision improvement exceeds measurement and delay costs."
    else: reason="Additional information does not have positive net estimated value."
    return {"evaluated":True,"net_voi":round(net,6),"collect_information":collect,"reason":reason}

def decide(request: dict[str, Any]) -> dict[str, Any]:
    p, evidence_details = reliability_adjusted_probability(
        request["prior_threat_probability"],
        request.get("evidence", []),
    )
    risk_limit = float(request["risk_limit"])
    lam = float(request["cvar_weight"])
    alpha = float(request["cvar_alpha"])

    scored = []
    rejected = []

    for raw in request.get("actions", []):
        action = dict(raw)
        utility, tail_loss, loss_method = action_utility(action, lam, alpha)

        row = {
            "action": action["action_type"],
            "label": action.get("label", action["action_type"]),
            "utility": round(utility, 6),
            "tail_loss": round(tail_loss, 6),
            "loss_method": loss_method,
            "serious_harm_probability": float(action["serious_harm_probability"]),
            "feasible": bool(action["feasible"]),
            "supported_by_evidence": bool(action["supported_by_evidence"]),
            "requires_human_approval": bool(
                action.get("requires_human_approval", False)
            ),
        }

        if not row["feasible"]:
            rejected.append({
                **row,
                "rejection_reason": "Action is not currently feasible.",
            })
        elif not row["supported_by_evidence"]:
            rejected.append({
                **row,
                "rejection_reason": (
                    "Insufficient crop/threat-specific evidence to support this action."
                ),
            })
        elif row["serious_harm_probability"] > risk_limit:
            rejected.append({
                **row,
                "rejection_reason": (
                    "Estimated serious-harm probability exceeds risk_limit."
                ),
            })
        else:
            scored.append(row)

    scored.sort(key=lambda x: x["utility"], reverse=True)

    if scored:
        chosen = scored[0]
        chosen_action = chosen["action"]
        status = (
            "human_approval_required"
            if chosen["requires_human_approval"]
            else "recommendation"
        )
    else:
        chosen = {
            "action": "ESCALATE",
            "label": "Escalate for human review",
            "utility": None,
            "tail_loss": None,
            "serious_harm_probability": None,
            "requires_human_approval": True,
        }
        chosen_action = "ESCALATE"
        status = "human_review_required"

    voi = calculate_net_voi(request.get("voi"))
    recovery = recovery_check(request.get("recovery"))
    action_types = {x["action"] for x in scored}

    # Positive VoI is advisory and must not override utility ranking.
    voi["verification_selected"] = bool(
        voi["collect_information"] and chosen_action == "VERIFY"
    )

    reasons = [
        "Threat probability is an evidence-adjusted estimate, not a validated diagnosis."
    ]

    if not scored:
        reasons.append(
            "No candidate action satisfied feasibility, evidence-support, and risk constraints."
        )

    if recovery["reassessment_required"]:
        reasons.append(
            "ROLA-style recovery discrepancy triggered reassessment; "
            "this does not automatically recalibrate a model."
        )

    if voi["collect_information"] and not voi["verification_selected"]:
        if "VERIFY" not in action_types:
            reasons.append(
                "Information has positive estimated net value, but no eligible "
                "VERIFY candidate was supplied; selected action was retained."
            )
        else:
            reasons.append(
                "Information has positive estimated net value, but VERIFY was "
                "not the highest-utility eligible action; selected action was retained."
            )

    return {
        "engine": "FLAI-constrained-v1",
        "mode": "recommendation_only",
        "status": status,
        "threat_probability": round(p, 6),
        "evidence_contributions": evidence_details,
        "selected_action": chosen_action,
        "selected_action_details": chosen,
        "eligible_actions": scored,
        "rejected_actions": rejected,
        "net_voi": voi,
        "recovery_assessment": recovery,
        "reassessment_required": recovery["reassessment_required"],
        "rola_assessment_recommended": recovery["reassessment_required"],
        "risk_limit": risk_limit,
        "cvar_alpha": alpha,
        "cvar_weight": lam,
        "reasons": reasons,
        "actuation_enabled": False,
    }
def compare_policies(request: dict[str, Any], fixed_threshold: float = 0.5) -> dict[str, Any]:
    """Research-only comparison. Baselines are evaluated, never actuated."""
    result = decide(request)
    p = result["threat_probability"]
    actions = request.get("actions", [])

    candidates = [
        a for a in actions
        if a.get("feasible", False) and a.get("supported_by_evidence", False)
    ]

    def pick(action):
        if action is None:
            return {
                "selected_action": "ESCALATE",
                "utility": None,
                "risk_limit_violated": False,
            }
        return {
            "selected_action": action["action_type"],
            "utility": round(
                action_utility(action, 0.0, request.get("cvar_alpha", 0.95))[0],
                6,
            ),
            "risk_limit_violated": (
                float(action["serious_harm_probability"])
                > float(request["risk_limit"])
            ),
        }

    monitor = next(
        (a for a in candidates if a["action_type"] == "MONITOR"), None
    )
    treat = next(
        (a for a in candidates if a["action_type"] == "TREAT"), None
    )

    fixed = pick(
        (treat if p >= fixed_threshold else monitor) or (treat or monitor)
    )
    risk = pick(
        min(
            candidates,
            key=lambda a: (
                float(a["serious_harm_probability"]),
                -float(a["expected_recovery_benefit"]),
            ),
        ) if candidates else None
    )
    eu = pick(
        max(
            candidates,
            key=lambda a: action_utility(
                a, 0.0, request.get("cvar_alpha", 0.95)
            )[0],
        ) if candidates else None
    )

    selected = result["selected_action"]
    details = result["selected_action_details"]
    constrained = {
        "selected_action": selected,
        "utility": details.get("utility"),
        "risk_limit_violated": (
            False if selected == "ESCALATE"
            else float(details["serious_harm_probability"])
            > float(request["risk_limit"])
        ),
    }

    return {
        "mode": "offline_policy_comparison_only",
        "fixed_threshold": fixed_threshold,
        "policies": {
            "fixed_threshold": fixed,
            "risk_only": risk,
            "expected_utility": eu,
            "flai_constrained_recovery_aware": constrained,
        },
        "note": (
            "Baseline policies are comparison outputs only. Do not actuate them. "
            "FLAI production recommendation remains constrained and recommendation-only."
        ),
    }