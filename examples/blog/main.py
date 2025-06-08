from datetime import datetime, UTC
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.binary import BinaryCriteria, BinaryFilterType
from fastapi_filterdeps.generic.time import TimeRangeCriteria
from fastapi_filterdeps.join.exists import JoinExistsCriteria
from fastapi_filterdeps.order_by import order_by_params

from database import get_db, init_db
from models import Post, User, Comment


async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Blog API Example", lifespan=lifespan)


# Create filter dependencies
post_filters = create_combined_filter_dependency(
    BinaryCriteria(
        field="is_published",
        alias="published",
        filter_type=BinaryFilterType.IS_TRUE,
    ),
    TimeRangeCriteria(
        field="created_at",
    ),
    JoinExistsCriteria(
        filter_condition=[Comment.is_approved == True],
        join_condition=Post.id == Comment.post_id,
        alias="has_approved_comments",
        join_model=Comment,
    ),
    orm_model=Post,
)


@app.get("/")
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


@app.get("/posts", response_model=List[dict])
async def list_posts(
    db: Session = Depends(get_db),
    filters=Depends(post_filters),
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
    return [
        {
            "id": post.id,
            "title": post.title,
            "author_id": post.author_id,
            "is_published": post.is_published,
            "view_count": post.view_count,
            "created_at": post.created_at,
            "updated_at": post.updated_at,
        }
        for post in result
    ]


@app.post("/users", response_model=dict)
async def create_user(username: str, email: str, db: Session = Depends(get_db)):
    """Create a new user"""
    user = User(username=username, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }


@app.post("/posts", response_model=dict)
async def create_post(
    title: str,
    content: str,
    author_id: int,
    db: Session = Depends(get_db),
):
    """Create a new post"""
    # Check if author exists
    author = db.get(User, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    post = Post(
        title=title,
        content=content,
        author_id=author_id,
        created_at=datetime.now(UTC),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {
        "id": post.id,
        "title": post.title,
        "author_id": post.author_id,
        "is_published": post.is_published,
        "view_count": post.view_count,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }


@app.post("/posts/{post_id}/comments", response_model=dict)
async def create_comment(
    post_id: int,
    content: str,
    author_id: int,
    db: Session = Depends(get_db),
):
    """Create a new comment on a post"""
    # Check if post exists
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check if author exists
    author = db.get(User, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    comment = Comment(
        content=content,
        post_id=post_id,
        author_id=author_id,
        created_at=datetime.now(UTC),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {
        "id": comment.id,
        "content": comment.content,
        "post_id": comment.post_id,
        "author_id": comment.author_id,
        "is_approved": comment.is_approved,
        "created_at": comment.created_at,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
