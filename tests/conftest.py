from typing import Callable
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import logging

from sqlalchemy.pool import StaticPool

from tests.models import Base, BasicModel


# Configure logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


@pytest.fixture(scope="function")
def engine():
    """Test SQLite database engine fixture."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Make sure to create tables for Vote and Review models
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """Database session fixture for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


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
    def setup(self, test_app, test_client, db_session):
        """Setup test environment."""
        self.app = test_app
        self.client = test_client
        self.session = db_session
        self.test_data = self.build_test_data()

        db_session.add_all(self.test_data)
        db_session.commit()

        yield

        db_session.query(BasicModel).delete()
        db_session.commit()

    def build_test_data(self):
        """Build test data.

        This is a base implementation that should be overridden by test classes
        that need specific test data.
        """
        return [
            BasicModel(
                name="Item 1",
                category="A",
                value=100,
                count=10,
                is_active=True,
                status="active",
                detail={"settings": {"theme": "light"}},
            ),
            BasicModel(
                name="Item 2",
                category="A",
                value=200,
                count=20,
                is_active=False,
                status="inactive",
                detail={"settings": {"theme": "dark"}},
            ),
            BasicModel(
                name="Item 3",
                category="B",
                value=150,
                count=15,
                is_active=None,
                status="pending",
                detail={"settings": {"theme": "custom"}},
            ),
        ]

    def setup_filter(self, filter_deps: Callable):
        """Setup filter dependency."""

        @self.app.get("/test-items")
        async def test_endpoint(filters=Depends(filter_deps)):
            stmt = select(BasicModel).where(*filters)
            result = self.session.execute(stmt).scalars().all()
            return result
