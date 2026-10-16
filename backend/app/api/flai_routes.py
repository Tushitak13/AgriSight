from fastapi import APIRouter
from app.schemas.flai_schema import FLAIDecisionRequest, PolicyComparisonRequest
from app.services.learning.flai_engine import decide, compare_policies

router = APIRouter(prefix="/api/flai", tags=["FLAI"])

@router.post("/decide")
def flai_decide(payload: FLAIDecisionRequest):
    """Return a recommendation only. This endpoint does not actuate hardware."""
    return decide(payload.model_dump())

@router.post("/compare")
def flai_compare(payload: PolicyComparisonRequest):
    """Compare simple baselines offline; comparison outputs must not actuate hardware."""
    data=payload.model_dump()
    threshold=data.pop("fixed_threshold",0.5)
    return compare_policies(data, fixed_threshold=threshold)
