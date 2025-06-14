from datetime import datetime, UTC
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Boolean
from enum import Enum


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )


class PostStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=PostStatus.DRAFT.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"))
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    score: Mapped[int] = mapped_column(Integer)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"))
