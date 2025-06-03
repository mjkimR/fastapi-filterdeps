import pytest
from sqlalchemy import create_engine, String, Integer, select
from sqlalchemy.orm import sessionmaker, mapped_column, Mapped, DeclarativeBase, Session
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from typing import List, Callable
import logging

# Configure logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


# Define test model
class Base(DeclarativeBase):
    pass


class TestModel(Base):
    __tablename__ = "test_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(50))
    value: Mapped[int] = mapped_column(Integer)


@pytest.fixture(scope="session")
def engine():
    """Creates a test SQLite database engine."""
    engine = create_engine("sqlite:///test.db", echo=True)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_data():
    """Provides test data for the test cases"""
    return [
        TestModel(name="Item 1", category="A", value=100),
        TestModel(name="Item 2", category="A", value=200),
        TestModel(name="Item 3", category="B", value=150),
        TestModel(name="Item 4", category="B", value=300),
    ]


@pytest.fixture(scope="function")
def db_session(engine, test_data):
    """Creates a test database session."""
    Session = sessionmaker(bind=engine)
    session = Session()

    # Add test data
    session.add_all(test_data)
    session.commit()

    yield session

    # Clean up test data
    session.query(TestModel).delete()
    session.commit()
    session.close()


def generate_app_client(filter_deps: Callable, db_session: Session):
    app = FastAPI()

    def get_db():
        yield db_session

    @app.get("/test-items", response_model=List[dict])
    async def get_items(db=Depends(get_db), filters=Depends(filter_deps)):
        stmt = select(TestModel).where(*filters)
        result = db.execute(stmt).scalars().all()
        return [{"id": r.id, "name": r.name, "category": r.category, "value": r.value} for r in result]

    return TestClient(app)
