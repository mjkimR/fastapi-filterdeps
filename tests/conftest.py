import os
from pathlib import Path
import sys
from typing import Callable
import pytest
from sqlalchemy import select
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import logging

from tests.models import BasicModel, Vote, Review, Comment
from tests.db_sessions import *
from tests.init_data import *

# Configure logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

sys.path.append(str(Path(__file__).parent.parent / "src"))

from fastapi_filterdeps.json.strategy import (
    JsonExtractStrategy,
    JsonOperatorStrategy,
    JsonStrategy,
)


def pytest_addoption(parser):
    """'--db-type' command line option to select DB type."""
    parser.addoption(
        "--db-type",
        action="store",
        default="all",
        help="Select database type for tests (sqlite, postgres, all)",
    )


@pytest.fixture(scope="session", params=["sqlite", "postgres"])
def db_type(request):
    """
    fixture to determine the database type for tests.
    Uses the '--db-type' command line option.
    """
    selected_db = request.config.getoption("--db-type")
    if selected_db != "all" and request.param != selected_db:
        pytest.skip(
            f"'{request.param}' skipped because '--db-type' is set to '{selected_db}'"
        )
    return request.param


@pytest.fixture(scope="function")
def db_session(request, db_type):
    """
    Fixture to provide a database session based on the selected DB type.
    Uses the db_type fixture to dynamically select the appropriate session fixture.
    """
    session_fixture = request.getfixturevalue(f"{db_type}_session")
    yield session_fixture


@pytest.fixture(scope="function")
def json_strategy(db_session) -> JsonStrategy:
    """
    Provides the appropriate JSON strategy by introspecting the active db_session.
    """
    dialect = db_session.bind.dialect.name
    if dialect == "postgresql":
        return JsonOperatorStrategy()
    elif dialect == "sqlite":
        return JsonExtractStrategy()
    else:
        raise NotImplementedError(f"No JSON strategy for dialect: {dialect}")


@pytest.fixture(scope="function")
def test_app(db_session):
    """FastAPI test application fixture."""
    app = FastAPI()

    def get_db():
        yield db_session

    app.dependency_overrides[get_db] = get_db
    return app


@pytest.fixture(scope="function")
def test_client(test_app):
    """FastAPI test client fixture."""
    return TestClient(test_app)


class BaseFilterTest:
    @pytest.fixture(autouse=True, scope="function")
    def setup(self, test_app, test_client, db_session, datasets):
        """Setup test environment."""
        self.app = test_app
        self.client = test_client
        self.session = db_session
        self.test_data = datasets

        for data in self.test_data.values():
            db_session.add_all(data)
        db_session.commit()

        yield

        db_session.query(Comment).delete()
        db_session.query(Review).delete()
        db_session.query(Vote).delete()
        db_session.query(BasicModel).delete()
        db_session.commit()

    def setup_filter(self, filter_deps: Callable):
        """Setup filter dependency."""

        @self.app.get("/test-items")
        async def test_endpoint(filters=Depends(filter_deps)):
            stmt = select(BasicModel).where(*filters)
            result = self.session.execute(stmt).scalars().all()
            return result

    def setup_vote_filter(self, filter_deps: Callable):
        """Setup filter dependency for Vote model"""

        @self.app.get("/test-votes")
        async def test_endpoint(filters=Depends(filter_deps)):
            stmt = select(Vote).where(*filters)
            result = self.session.execute(stmt).scalars().all()
            return result

    def setup_review_filter(self, filter_deps: Callable):
        """Setup filter dependency for Review model"""

        @self.app.get("/test-reviews")
        async def test_endpoint(filters=Depends(filter_deps)):
            stmt = select(Review).where(*filters)
            result = self.session.execute(stmt).scalars().all()
            return result

    def setup_comment_filter(self, filter_deps: Callable):
        """Setup filter dependency for Comment model"""

        @self.app.get("/test-comments")
        async def test_endpoint(filters=Depends(filter_deps)):
            stmt = select(Comment).where(*filters)
            result = self.session.execute(stmt).scalars().all()
            return result
