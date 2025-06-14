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
    users = [
        User(id=1, username="admin", email="admin@example.com"),
        User(id=2, username="user", email="user@example.com"),
        User(id=3, username="user2", email="user2@example.com"),
        User(id=4, username="user3", email="user3@example.com"),
    ]
    posts = [
        Post(
            id=1,
            title="Hello World",
            content="This is a test post 1",
            author_id=1,
            is_published=True,
        ),
        Post(
            id=2,
            title="Another Post",
            content="This is a test post 2",
            author_id=2,
            is_published=True,
        ),
        Post(
            id=3,
            title="Another Post 2",
            content="This is a test post 3",
            author_id=2,
            is_published=False,
        ),
    ]
    comments = [
        Comment(
            id=1,
            content="This is a test comment",
            post_id=1,
            author_id=2,
            is_approved=True,
        ),
        Comment(
            id=2,
            content="This is a test comment 2",
            post_id=2,
            author_id=1,
            is_approved=True,
        ),
        Comment(
            id=3,
            content="This is a test comment 3",
            post_id=3,
            author_id=1,
            is_approved=False,
        ),
    ]
    votes = [
        Vote(id=1, score=1, post_id=1),
        Vote(id=2, score=2, post_id=2),
        Vote(id=3, score=4, post_id=3),
        Vote(id=4, score=5, post_id=3),
    ]
    db.add_all(users)
    db.add_all(posts)
    db.add_all(comments)
    db.add_all(votes)
    # Commit the changes
    db.commit()
    db.close()
