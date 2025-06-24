from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Post, User, Comment, Vote

# SQLite database for example
DATABASE_URL = "sqlite:///:memory:"

# Create engine with check_same_thread=False for SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    from datetime import datetime, UTC, timedelta

    now = datetime.now(UTC)
    users = [
        User(
            id=1,
            username="admin",
            email="admin@example.com",
            is_active=True,
            created_at=now - timedelta(days=30),
        ),
        User(
            id=2,
            username="user",
            email="user@example.com",
            is_active=True,
            created_at=now - timedelta(days=20),
        ),
        User(
            id=3,
            username="inactive_user",
            email="inactive@example.com",
            is_active=False,
            created_at=now - timedelta(days=10),
        ),
        User(
            id=4,
            username="alice",
            email="alice@example.com",
            is_active=True,
            created_at=now - timedelta(days=5),
        ),
        User(
            id=5,
            username="bob",
            email="bob@example.com",
            is_active=True,
            created_at=now - timedelta(days=2),
        ),
        User(
            id=6,
            username="charlie",
            email="charlie@example.com",
            is_active=False,
            created_at=now - timedelta(days=1),
        ),
    ]
    posts = [
        Post(
            id=1,
            title="Hello World",
            content="This is a test post 1",
            author_id=1,
            is_published=True,
            view_count=100,
            status="published",
            created_at=now - timedelta(days=29),
            updated_at=now - timedelta(days=28),
        ),
        Post(
            id=2,
            title="Another Post",
            content="This is a test post 2",
            author_id=2,
            is_published=True,
            view_count=50,
            status="draft",
            created_at=now - timedelta(days=19),
            updated_at=None,
        ),
        Post(
            id=3,
            title="Archived Post",
            content="This is an archived post",
            author_id=3,
            is_published=False,
            view_count=0,
            status="archived",
            created_at=now - timedelta(days=9),
            updated_at=None,
        ),
        Post(
            id=4,
            title="Alice's Adventures",
            content="Alice writes about adventures.",
            author_id=4,
            is_published=True,
            view_count=200,
            status="published",
            created_at=now - timedelta(days=4),
            updated_at=now - timedelta(days=2),
        ),
        Post(
            id=5,
            title="Bob's Thoughts",
            content="Bob shares his thoughts.",
            author_id=5,
            is_published=False,
            view_count=5,
            status="draft",
            created_at=now - timedelta(days=1),
            updated_at=None,
        ),
        Post(
            id=6,
            title="Inactive User Post",
            content="Post by inactive user.",
            author_id=6,
            is_published=False,
            view_count=1,
            status="draft",
            created_at=now,
            updated_at=None,
        ),
    ]
    comments = [
        Comment(
            id=1,
            content="Great post!",
            post_id=1,
            author_id=2,
            is_approved=True,
            created_at=now - timedelta(days=28),
        ),
        Comment(
            id=2,
            content="Thanks for sharing.",
            post_id=1,
            author_id=4,
            is_approved=True,
            created_at=now - timedelta(days=27),
        ),
        Comment(
            id=3,
            content="Interesting thoughts.",
            post_id=2,
            author_id=1,
            is_approved=True,
            created_at=now - timedelta(days=18),
        ),
        Comment(
            id=4,
            content="I disagree.",
            post_id=2,
            author_id=5,
            is_approved=False,
            created_at=now - timedelta(days=17),
        ),
        Comment(
            id=5,
            content="Why archived?",
            post_id=3,
            author_id=4,
            is_approved=True,
            created_at=now - timedelta(days=8),
        ),
        Comment(
            id=6,
            content="Nice adventure!",
            post_id=4,
            author_id=1,
            is_approved=True,
            created_at=now - timedelta(days=3),
        ),
        Comment(
            id=7,
            content="Inactive user comment.",
            post_id=5,
            author_id=3,
            is_approved=False,
            created_at=now - timedelta(days=1),
        ),
    ]
    votes = [
        Vote(id=1, score=1, post_id=1),
        Vote(id=2, score=2, post_id=1),
        Vote(id=3, score=3, post_id=2),
        Vote(id=4, score=4, post_id=3),
        Vote(id=5, score=5, post_id=4),
        Vote(id=6, score=1, post_id=4),
        Vote(id=7, score=2, post_id=5),
        Vote(id=8, score=3, post_id=6),
    ]
    db.add_all(users)
    db.add_all(posts)
    db.add_all(comments)
    db.add_all(votes)
    db.commit()
    db.close()
