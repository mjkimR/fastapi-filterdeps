from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from examples.blog.api.filters import CreatedAtFilterSet
from fastapi_filterdeps.filters.column.binary import BinaryCriteria, BinaryFilterType
from fastapi_filterdeps.filters.column.string import StringCriteria, StringMatchType

from database import get_db
from models import Comment, Post, User
from schemas import CommentRead, CommentCreate

router = APIRouter(prefix="/comments", tags=["Comments"])


class CommentFilterSet(CreatedAtFilterSet):
    class Meta:
        orm_model = Comment

    # String: content
    content = StringCriteria(
        field="content",
        match_type=StringMatchType.CONTAINS,
    )
    # Binary: is_approved
    is_approved = BinaryCriteria(
        field="is_approved",
        filter_type=BinaryFilterType.IS_TRUE,
    )


@router.get("", response_model=List[CommentRead])
async def list_comments(
    db: Session = Depends(get_db),
    filters=Depends(CommentFilterSet),
):
    query = select(Comment).where(*filters)
    result = db.execute(query).scalars().all()
    return result


@router.post("", response_model=CommentRead)
async def create_comment(
    comment: CommentCreate,
    db: Session = Depends(get_db),
):
    """Create a new comment"""
    # Check if the author exists
    author = db.get(User, post.author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    # Check if the post exists
    post = db.get(Post, comment.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comment_obj = Comment(
        content=comment.content,
        post_id=comment.post_id,
        author_id=comment.author_id,
        is_approved=comment.is_approved if hasattr(comment, "is_approved") else True,
    )
    db.add(comment_obj)
    db.commit()
    db.refresh(comment_obj)
    return comment_obj
