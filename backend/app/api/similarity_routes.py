from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import DEFAULT_DEVICE_ID
from app.database.database import get_db
from app.schemas.experience_schema import ExperienceOut, SimilarityResult, SimilaritySearchIn
from app.services.similarity.retrieval import find_similar, find_similar_to_current
from app.utils import constants as K

router = APIRouter(prefix="/api/similarity", tags=["similarity"])


def _to_result(raw: dict, excluded: list[str]) -> dict:
    matches = [dict(**cmp, experience=ExperienceOut.model_validate(exp)) for exp, cmp in raw["matches"]]
    return {**raw, "matches": matches, "excluded_fields": excluded}


@router.post("/search", response_model=SimilarityResult)
def search(payload: SimilaritySearchIn, db: Session = Depends(get_db)):
    """Find past experiences similar to a condition you supply."""
    raw = find_similar(db, payload.device_id or DEFAULT_DEVICE_ID, payload.condition.as_dict(),
                       payload.k, payload.min_similarity, payload.only_with_outcome)
    return _to_result(raw, [])


@router.get("/current", response_model=SimilarityResult)
def similar_to_current(device_id: str = DEFAULT_DEVICE_ID,
                       k: int = Query(K.SIMILARITY_DEFAULT_K, ge=1, le=50),
                       min_similarity: float = Query(K.SIMILARITY_MIN_SCORE, ge=0, le=1),
                       only_with_outcome: bool = False,
                       exclude_unreliable: bool = True,
                       db: Session = Depends(get_db)):
    """Find past experiences similar to the device's latest reading. By default, sensors the
    reliability engine distrusts are left out of the query so a faulty value cannot drive retrieval."""
    found = find_similar_to_current(db, device_id, k, min_similarity, only_with_outcome, exclude_unreliable)
    if found is None:
        raise HTTPException(status_code=404, detail="no readings for this device")
    raw, excluded = found
    return _to_result(raw, excluded)
