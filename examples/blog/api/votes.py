from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from fastapi_filterdeps.filtersets import FilterSet
from fastapi_filterdeps.filters.column.numeric import NumericCriteria, NumericFilterType

from database import get_db
from models import Post, Vote
from schemas import VoteRead, VoteCreate

router = APIRouter(prefix="/votes", tags=["Votes"])


class VoteFilterSet(FilterSet):
    class Meta:
        orm_model = Vote

    # Numeric: score
    min_score = NumericCriteria(
        field="score",
        operator=NumericFilterType.GTE,
        numeric_type=int,
    )
    max_score = NumericCriteria(
        field="score",
        operator=NumericFilterType.LTE,
        numeric_type=int,
    )


@router.get("", response_model=List[VoteRead])
async def list_votes(
    db: Session = Depends(get_db),
    filters=Depends(VoteFilterSet),
):
    query = select(Vote).where(*filters)
    result = db.execute(query).scalars().all()
    return result


@router.post("", response_model=VoteRead)
async def create_vote(
    vote: VoteCreate,
    db: Session = Depends(get_db),
):
    """Create a new vote on a post"""
    # Check if post exists
    post_obj = db.get(Post, vote.post_id)
    if not post_obj:
        raise HTTPException(status_code=404, detail="Post not found")

    vote_obj = Vote(
        score=vote.score,
        post_id=vote.post_id,
    )
    db.add(vote_obj)
    db.commit()
    db.refresh(vote_obj)
    return vote_obj
