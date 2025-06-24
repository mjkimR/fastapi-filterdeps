from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from fastapi_filterdeps.filtersets import FilterSet
from fastapi_filterdeps.filters.column.binary import BinaryCriteria, BinaryFilterType
from fastapi_filterdeps.filters.column.time import TimeCriteria, TimeMatchType
from fastapi_filterdeps.filters.column.string import (
    StringCriteria,
    StringSetCriteria,
    StringMatchType,
)

from database import get_db
from models import User
from schemas import UserRead, UserCreate

router = APIRouter(prefix="/users", tags=["Users"])


class UserFilterSet(FilterSet):
    class Meta:
        orm_model = User

    # String: username
    username = StringCriteria(
        field="username",
        match_type=StringMatchType.CONTAINS,
    )
    # StringSet: email
    emails = StringSetCriteria(
        field="email",
    )
    # Binary: is_active
    active = BinaryCriteria(
        field="is_active",
        filter_type=BinaryFilterType.IS_TRUE,
    )
    # Time range: created_at
    created_at_start = TimeCriteria(
        field="created_at",
        match_type=TimeMatchType.GTE,
    )
    created_at_end = TimeCriteria(
        field="created_at",
        match_type=TimeMatchType.LTE,
    )


@router.get("", response_model=List[UserRead])
async def list_users(
    db: Session = Depends(get_db),
    filters=Depends(UserFilterSet),
):
    query = select(User).where(*filters)
    result = db.execute(query).scalars().all()
    return result


@router.post("", response_model=UserRead)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    user_obj = User(username=user.username, email=user.email, is_active=user.is_active)
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj
