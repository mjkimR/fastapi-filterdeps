from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PostRead(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    is_published: bool
    view_count: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class PostCreate(BaseModel):
    title: str
    content: str
    author_id: int
    is_published: bool = False
    view_count: int = 0
    status: str = "draft"


class CommentRead(BaseModel):
    id: int
    content: str
    post_id: int
    author_id: int
    is_approved: bool
    created_at: datetime


class CommentCreate(BaseModel):
    content: str
    post_id: int
    author_id: int
    is_approved: bool = True


class UserRead(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    email: str
    is_active: bool = True


class VoteRead(BaseModel):
    id: int
    score: int
    post_id: int


class VoteCreate(BaseModel):
    score: int
    post_id: int
