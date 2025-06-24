from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from examples.blog.api.filters import CreatedAtFilterSet, TitleFilterSet
from fastapi_filterdeps.core.decorators import for_filter
from fastapi_filterdeps.filters.column.binary import BinaryCriteria, BinaryFilterType
from fastapi_filterdeps.filters.column.enum import EnumCriteria, MultiEnumCriteria
from fastapi_filterdeps.filters.column.numeric import (
    NumericCriteria,
    NumericFilterType,
)
from fastapi_filterdeps.filters.relation.having import GroupByHavingCriteria
from fastapi_filterdeps.filters.relation.exists import JoinExistsCriteria
from fastapi_filterdeps.order_by import order_by_params

from database import get_db
from models import Post, User, Comment, PostStatus, Vote
from schemas import PostRead, PostCreate


router = APIRouter(prefix="/posts", tags=["Posts"])


@for_filter(
    field="view_count", description="Custom filter for view count", bound_type=bool
)
def custom_filter(orm_model, value):
    """Custom filter logic example."""
    # Example logic: return posts with view_count >= 10 if value is True,
    # or posts with view_count < 10 if value is False.
    # If value is None, return all posts.
    if value is None:
        return None
    if value:
        return orm_model.view_count >= 10
    else:
        return orm_model.view_count < 10


class PostFilterSet(TitleFilterSet, CreatedAtFilterSet):
    class Meta:
        orm_model = Post

    # Binary: is_published
    is_published = BinaryCriteria(
        field="is_published",
        filter_type=BinaryFilterType.IS_TRUE,
    )
    # Enum: status
    status = EnumCriteria(
        field="status",
        enum_class=PostStatus,
    )
    # MultiEnum: status (multi)
    statuses = MultiEnumCriteria(
        field="status",
        enum_class=PostStatus,
    )
    # Numeric range: view_count
    min_views = NumericCriteria(
        field="view_count",
        operator=NumericFilterType.GTE,
        numeric_type=int,
    )
    max_views = NumericCriteria(
        field="view_count",
        operator=NumericFilterType.LTE,
        numeric_type=int,
    )
    # Numeric exact: view_count
    views = NumericCriteria(
        field="view_count",
        numeric_type=int,
        operator=NumericFilterType.EQ,
    )
    # JoinExists: has approved comments
    has_approved_comments = JoinExistsCriteria(
        filter_condition=[Comment.is_approved == True],
        join_condition=Post.id == Comment.post_id,
        join_model=Comment,
    )
    # GroupByHaving: average vote score >= x
    avg_vote_score = GroupByHavingCriteria(
        value_type=float,
        group_by_cols=[Post.id],
        having_builder=lambda x: func.avg(Vote.score) >= x,
    )
    # Custom filter example (decorated with @for_filter)
    custom_view_count_filter = custom_filter


@router.get("", response_model=List[PostRead])
async def list_posts(
    db: Session = Depends(get_db),
    filters=Depends(PostFilterSet),
    order_by=Depends(
        order_by_params(Post, whitelist=["created_at", "view_count", "id"])
    ),
):
    """
    List posts with filtering options:
    - published: Filter by publication status
    - created: Filter by creation date range
    - has_approved_comments: Filter posts that have approved comments
    - order_by: Order by created_at, view_count, or id (prefix with - for descending)
    """
    query = select(Post).where(*filters)

    # Apply ordering
    if order_by:
        query = query.order_by(*order_by)

    result = db.execute(query).scalars().all()
    return result


@router.post("", response_model=PostRead)
async def create_post(
    post: PostCreate,
    db: Session = Depends(get_db),
):
    """Create a new post"""
    # Check if author exists
    author = db.get(User, post.author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    post_obj = Post(
        title=post.title,
        content=post.content,
        author_id=post.author_id,
        is_published=post.is_published,
        view_count=post.view_count,
        status=post.status,
    )
    db.add(post_obj)
    db.commit()
    db.refresh(post_obj)
    return post_obj
