from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, equal_to
from sqlalchemy import Engine

from pururu.infrastructure.adapters.postgres.engine import PostgresDBEngine


@pytest.fixture
def mock_create_engine():
    """Mock SQLAlchemy create_engine"""
    with patch('pururu.infrastructure.adapters.postgres.engine.create_engine') as mock:
        mock_engine = MagicMock(spec=Engine)
        mock.return_value = mock_engine
        yield mock


@pytest.fixture
def mock_base():
    """Mock Base metadata"""
    with patch('pururu.infrastructure.adapters.postgres.engine.Base') as mock:
        mock.metadata.create_all = MagicMock()
        yield mock


@pytest.fixture
def mock_settings():
    """Mock settings"""
    with patch('pururu.infrastructure.adapters.postgres.engine.settings') as mock:
        mock.database.postgres.echo = False
        yield mock


@pytest.mark.unit
def test_postgres_engine_initialization(mock_create_engine, mock_base, mock_settings):
    """Test PostgresDBEngine initializes with correct connection string"""
    # Arrange
    protocol = "postgresql+psycopg2"
    user = "testuser"
    password = "testpass"
    host = "localhost"
    port = 5432
    db_name = "postgres_db"

    # Act
    engine = PostgresDBEngine(protocol, user, password, host, port, db_name)

    # Assert
    expected_url = f"{protocol}://{user}:{password}@{host}:{port}/{db_name}"
    mock_create_engine.assert_called_once()
    call_args = mock_create_engine.call_args[0]
    assert_that(call_args[0], equal_to(expected_url))


@pytest.mark.unit
def test_postgres_engine_loads_metadata(mock_create_engine, mock_base, mock_settings):
    """Test PostgresDBEngine loads metadata on initialization"""
    # Act
    engine = PostgresDBEngine("postgresql+psycopg2", "user", "pass", "localhost", 5432, "postgres")

    # Assert
    mock_base.metadata.create_all.assert_called_once_with(engine.engine)


@pytest.mark.unit
def test_get_engine_returns_engine(mock_create_engine, mock_base, mock_settings):
    """Test get_engine returns SQLAlchemy engine"""
    # Arrange
    engine = PostgresDBEngine("postgresql+psycopg2", "user", "pass", "localhost", 5432, "postgres")

    # Act
    result = engine.get_engine()

    # Assert
    assert_that(result, equal_to(engine.engine))


@pytest.mark.unit
def test_load_metadata_creates_tables(mock_create_engine, mock_base, mock_settings):
    """Test load_metadata creates all tables"""
    # Arrange
    engine = PostgresDBEngine("postgresql+psycopg2", "user", "pass", "localhost", 5432, "postgres")
    mock_base.metadata.create_all.reset_mock()

    # Act
    engine.load_metadata()

    # Assert
    mock_base.metadata.create_all.assert_called_once_with(engine.engine)
