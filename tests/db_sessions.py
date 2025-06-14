import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.mysql import MySqlContainer
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from tests.models import Base


@pytest.fixture(scope="session")
def sqlite_engine():
    """Test SQLite database engine fixture."""
    engine = sqlalchemy.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=sqlalchemy.StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def sqlite_session(sqlite_engine):
    """Database session fixture for SQLite testing."""
    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def postgres_engine_fixture():
    """Fixture to create a PostgreSQL container for testing."""
    with PostgresContainer("postgres:16") as postgres:
        engine = sqlalchemy.create_engine(postgres.get_connection_url())
        Base.metadata.create_all(engine)
        yield engine
        Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def postgres_session(postgres_engine_fixture):
    """Database session fixture for testing."""
    Session = sessionmaker(bind=postgres_engine_fixture)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def mysql_engine():
    with MySqlContainer("mysql:8.0") as mysql:
        engine = sqlalchemy.create_engine(mysql.get_connection_url())
        Base.metadata.create_all(engine)
        yield engine
        Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def mysql_session(mysql_engine):
    """Database session fixture for MySQL testing."""
    Session = sessionmaker(bind=mysql_engine)
    session = Session()
    yield session
    session.close()
