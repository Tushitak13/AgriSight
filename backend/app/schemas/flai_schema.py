from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    likelihood_ratio: float = Field(gt=0, description="Calibrated P(evidence|threat)/P(evidence|no threat)")
    quality: float = Field(ge=0, le=1)
    freshness: float = Field(ge=0, le=1)
    validity: float = Field(ge=0, le=1)

class ActionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: str = Field(min_length=1, max_length=40, description="Examples: MONITOR, VERIFY, IRRIGATE, TREAT, ESCALATE")
    label: Optional[str] = Field(default=None, max_length=120)
    expected_recovery_benefit: float = Field(description="Crop/threat-specific estimated benefit, in consistent utility units")
    action_cost: float = Field(default=0, ge=0)
    resource_cost: float = Field(default=0, ge=0)
    side_effect_cost: float = Field(default=0, ge=0)
    serious_harm_probability: float = Field(ge=0, le=1)
    serious_harm_loss: float = Field(default=100, ge=0, description="Utility-scale harm loss proxy if no loss samples supplied")
    loss_samples: List[float] = Field(default_factory=list, max_length=10000, description="Optional simulated loss samples for CVaR")
    feasible: bool = True
    supported_by_evidence: bool = True
    requires_human_approval: bool = False

class VOIInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provided: bool = True
    expected_best_utility_after_observation: float
    current_best_utility: float
    measurement_cost: float = Field(ge=0)
    delay_cost: float = Field(ge=0)
    waiting_safe: bool


class RecoveryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provided: bool = True
    observed_value: float = Field(allow_inf_nan=False)
    expected_value: float = Field(allow_inf_nan=False)
    observed_variance: float = Field(ge=0, allow_inf_nan=False)
    expected_variance: float = Field(ge=0, allow_inf_nan=False)
    z_threshold: float = Field(default=2.0, gt=0, allow_inf_nan=False)
    evidence_valid: bool
    timing_appropriate: bool


class FLAIDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prior_threat_probability: float = Field(ge=0, le=1)
    evidence: List[EvidenceItem] = Field(default_factory=list, max_length=100)
    actions: List[ActionCandidate] = Field(min_length=1, max_length=50)
    risk_limit: float = Field(default=0.05, ge=0, le=1)
    cvar_weight: float = Field(default=1.0, ge=0)
    cvar_alpha: float = Field(default=0.95, ge=0, lt=1)
    voi: Optional[VOIInput] = None
    recovery: Optional[RecoveryInput] = None

class PolicyComparisonRequest(FLAIDecisionRequest):
    fixed_threshold: float = Field(default=0.5, ge=0, le=1)
