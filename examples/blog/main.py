from datetime import datetime, UTC
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from fastapi_filterdeps.filtersets import FilterSet, create_combined_filter_dependency
from fastapi_filterdeps.simple.binary import BinaryCriteria, BinaryFilterType
from fastapi_filterdeps.simple.time import TimeCriteria, TimeMatchType
from fastapi_filterdeps.simple.enum import EnumCriteria, MultiEnumCriteria
from fastapi_filterdeps.simple.numeric import (
    NumericCriteria,
    NumericFilterType,
)
from fastapi_filterdeps.simple.string import (
    StringCriteria,
    StringSetCriteria,
    StringMatchType,
)
from fastapi_filterdeps.simple.regex import RegexCriteria
from fastapi_filterdeps.complex.having import GroupByHavingCriteria
from fastapi_filterdeps.complex.join_exists import JoinExistsCriteria
from fastapi_filterdeps.order_by import order_by_params

from database import get_db, init_db
from models import Post, User, Comment, PostStatus, Vote
from schemas import (
    PostRead,
    PostCreate,
    CommentRead,
    CommentCreate,
    UserRead,
    UserCreate,
    VoteRead,
    VoteCreate,
)


async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Blog API Example", lifespan=lifespan)


class PostFilterSet(FilterSet):
    class Meta:
        orm_model = Post

    # Binary: is_published
    is_published = BinaryCriteria(
        field="is_published",
        alias="published",
        filter_type=BinaryFilterType.IS_TRUE,
    )
    # Enum: status
    status = EnumCriteria(
        field="status",
        alias="status",
        enum_class=PostStatus,
    )
    # MultiEnum: status (multi)
    statuses = MultiEnumCriteria(
        field="status",
        alias="statuses",
        enum_class=PostStatus,
    )
    # Numeric range: view_count
    min_views = NumericCriteria(
        field="view_count",
        alias="min_views",
        operator=NumericFilterType.GTE,
        numeric_type=int,
    )
    max_views = NumericCriteria(
        field="view_count",
        alias="max_views",
        operator=NumericFilterType.LTE,
        numeric_type=int,
    )
    # Numeric exact: view_count
    views = NumericCriteria(
        field="view_count",
        alias="views",
        numeric_type=int,
        operator=NumericFilterType.EQ,
    )
    # String: title contains
    title_contains = StringCriteria(
        field="title",
        alias="title",
        match_type=StringMatchType.CONTAINS,
    )
    # String set: title in set
    title_in_set = StringSetCriteria(
        field="title",
        alias="titles",
    )
    # Regex: title pattern
    title_pattern = RegexCriteria(
        field="title",
        alias="title_pattern",
        case_sensitive=False,
    )
    # Time range: created_at
    created_at_start = TimeCriteria(
        field="created_at",
        alias="created_at_start",
        match_type=TimeMatchType.GTE,
    )
    created_at_end = TimeCriteria(
        field="created_at",
        alias="created_at_end",
        match_type=TimeMatchType.LTE,
    )
    # JoinExists: has approved comments
    has_approved_comments = JoinExistsCriteria(
        filter_condition=[Comment.is_approved == True],
        join_condition=Post.id == Comment.post_id,
        alias="has_approved_comments",
        join_model=Comment,
    )
    # GroupByHaving: average vote score >= x
    avg_vote_score = GroupByHavingCriteria(
        alias="avg_vote_score",
        value_type=float,
        group_by_cols=[Post.id],
        having_builder=lambda x: func.avg(Vote.score) >= x,
    )


# User filters example
def user_filters():
    return create_combined_filter_dependency(
        StringCriteria(
            field="username", alias="username", match_type=StringMatchType.CONTAINS
        ),
        StringSetCriteria(field="email", alias="emails"),
        BinaryCriteria(
            field="is_active", alias="active", filter_type=BinaryFilterType.IS_TRUE
        ),
        TimeCriteria(
            field="created_at", alias="created_at_start", match_type=TimeMatchType.GTE
        ),
        TimeCriteria(
            field="created_at", alias="created_at_end", match_type=TimeMatchType.LTE
        ),
        orm_model=User,
    )


# Comment filters example
def comment_filters():
    return create_combined_filter_dependency(
        StringCriteria(
            field="content", alias="content", match_type=StringMatchType.CONTAINS
        ),
        BinaryCriteria(
            field="is_approved", alias="approved", filter_type=BinaryFilterType.IS_TRUE
        ),
        TimeCriteria(
            field="created_at", alias="created_at_start", match_type=TimeMatchType.GTE
        ),
        TimeCriteria(
            field="created_at", alias="created_at_end", match_type=TimeMatchType.LTE
        ),
        orm_model=Comment,
    )


# Vote filters example
def vote_filters():
    return create_combined_filter_dependency(
        NumericCriteria(
            field="score",
            alias="min_score",
            operator=NumericFilterType.GTE,
            numeric_type=int,
        ),
        NumericCriteria(
            field="score",
            alias="max_score",
            operator=NumericFilterType.LTE,
            numeric_type=int,
        ),
        orm_model=Vote,
    )


@app.get("/")
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


@app.get("/posts", response_model=List[PostRead])
async def list_posts(
    db: Session = Depends(get_db),
    filters=Depends(PostFilterSet.as_dependency()),
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


@app.get("/users", response_model=List[UserRead])
async def list_users(
    db: Session = Depends(get_db),
    filters=Depends(user_filters()),
):
    query = select(User).where(*filters)
    result = db.execute(query).scalars().all()
    return result


@app.get("/comments", response_model=List[CommentRead])
async def list_comments(
    db: Session = Depends(get_db),
    filters=Depends(comment_filters()),
):
    query = select(Comment).where(*filters)
    result = db.execute(query).scalars().all()
    return result


@app.get("/votes", response_model=List[VoteRead])
async def list_votes(
    db: Session = Depends(get_db),
    filters=Depends(vote_filters()),
):
    query = select(Vote).where(*filters)
    result = db.execute(query).scalars().all()
    return result


@app.post("/users", response_model=UserRead)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    user_obj = User(username=user.username, email=user.email, is_active=user.is_active)
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj


@app.post("/posts", response_model=PostRead)
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
        created_at=datetime.now(UTC),
    )
    db.add(post_obj)
    db.commit()
    db.refresh(post_obj)
    return post_obj


@app.post("/posts/{post_id}/comments", response_model=CommentRead)
async def create_comment(
    post_id: int,
    comment: CommentCreate,
    db: Session = Depends(get_db),
):
    """Create a new comment on a post"""
    # Check if post exists
    post_obj = db.get(Post, post_id)
    if not post_obj:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check if author exists
    author = db.get(User, comment.author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    comment_obj = Comment(
        content=comment.content,
        post_id=post_id,
        author_id=comment.author_id,
        is_approved=comment.is_approved,
        created_at=datetime.now(UTC),
    )
    db.add(comment_obj)
    db.commit()
    db.refresh(comment_obj)
    return comment_obj


@app.post("/votes", response_model=VoteRead)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
