"""
Centralized test data initialization for all DB backends.
Provides a single function to build and optionally insert all test data for all models.
"""

from datetime import datetime, timedelta, timezone

import pytest
from tests.models import Post, Comment, Vote, Review


@pytest.fixture(scope="function")
def datasets():
    """Returns a dict of lists of model instances for all test models."""
    now = datetime.now(timezone.utc)
    items = [
        Post(
            id=1,
            name="Item 1",
            category="A",
            value=100,
            count=10,
            is_active=True,
            status="active",
            detail={
                "settings": {"theme": "light"},
                "metadata": {"tags": ["urgent", "important"], "version": "1.0"},
                "tags": {
                    "urgent": True,
                    "language": "en",
                    "priority": "high",
                },
            },
            created_at=now - timedelta(days=10),
        ),
        Post(
            id=2,
            name="Item 2",
            category="A",
            value=200,
            count=20,
            is_active=False,
            status="inactive",
            detail={"settings": {"theme": "dark", "notifications": True}},
            created_at=now - timedelta(days=5),
        ),
        Post(
            id=3,
            name="Item 3",
            category="B",
            value=150,
            count=15,
            is_active=None,
            status="pending",
            detail={
                "settings": {
                    "theme": "custom",
                    "preferences": {"language": "en", "timezone": "Asia/Seoul"},
                }
            },
            created_at=now - timedelta(days=1),
        ),
        Post(
            id=4,
            name="Item 4",
            category="C",
            value=300,
            count=30,
            is_active=True,
            status="archived",
            detail={"settings": {"theme": "blue"}},
            created_at=now,
        ),
        Post(
            id=5,
            name="Item 5",
            category="C",
            value=250,
            count=25,
            is_active=False,
            status="active",
            detail={"settings": {"theme": "red"}},
            created_at=now - timedelta(days=3),
        ),
    ]

    # Comments related to items
    comments = [
        Comment(
            id=1,
            content="Comment 1 on Item 1",
            post_id=items[0].id,
            is_approved=True,
        ),
        Comment(
            id=2,
            content="Comment 2 on Item 1",
            post_id=items[0].id,
            is_approved=False,
        ),
        Comment(
            id=3,
            content="Comment 1 on Item 2",
            post_id=items[1].id,
            is_approved=True,
        ),
        Comment(
            id=4,
            content="Comment 1 on Item 3",
            post_id=items[2].id,
            is_approved=True,
        ),
        Comment(
            id=5,
            content="Comment 1 on Item 4",
            post_id=items[3].id,
            is_approved=False,
        ),
    ]
    votes = [
        Vote(id=1, score=1, post_id=items[0].id),
        Vote(id=2, score=2, post_id=items[1].id),
        Vote(id=3, score=4, post_id=items[2].id),
        Vote(id=4, score=5, post_id=items[2].id),
    ]
    reviews = [
        Review(
            id=1,
            rating=5,
            created_at=now - timedelta(days=2),
            post_id=items[0].id,
        ),
        Review(
            id=2,
            rating=3,
            created_at=now - timedelta(days=1),
            post_id=items[1].id,
        ),
        Review(id=3, rating=4, created_at=now, post_id=items[2].id),
    ]

    return {
        "items": items,
        "comments": comments,
        "votes": votes,
        "reviews": reviews,
    }
