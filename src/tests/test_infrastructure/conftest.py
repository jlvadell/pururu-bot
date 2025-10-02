"""Shared fixtures for infrastructure tests - external adapters and clients"""
from unittest.mock import MagicMock, AsyncMock

import pytest


# Google Sheets fixtures
@pytest.fixture
def mock_gspread_credentials():
    """Create mock Google Sheets credentials"""
    return MagicMock()


@pytest.fixture
def mock_gspread_client():
    """Create a mock gspread client"""
    mock_client = MagicMock()
    mock_client.open_by_key.return_value = MagicMock()
    return mock_client


@pytest.fixture
def mock_spreadsheet():
    """Create a mock Google Sheets spreadsheet with common operations"""
    mock = MagicMock()
    mock.values_get.return_value = {'values': []}
    mock.values_update.return_value = {'updatedCells': 1}
    return mock


# Postgres fixtures
@pytest.fixture
def mock_postgres_connection():
    """Create a mock PostgreSQL connection"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    return mock_conn


@pytest.fixture
def mock_postgres_pool():
    """Create a mock PostgreSQL connection pool"""
    mock_pool = AsyncMock()
    mock_conn = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    return mock_pool


@pytest.fixture
def mock_s3_client():
    """Create a mock AWS S3 client"""
    mock = MagicMock()
    mock.get_object.return_value = {'Body': MagicMock()}
    mock.put_object.return_value = {'ETag': 'etag-123'}
    return mock


# Discord fixtures
@pytest.fixture
def mock_discord_client():
    """Create a mock Discord client"""
    return AsyncMock()


@pytest.fixture
def mock_discord_channel():
    """Create a mock Discord channel"""
    mock = MagicMock()
    mock.id = 123456789
    mock.name = "test-channel"
    mock.send.return_value = AsyncMock(id=987654321)
    return mock


@pytest.fixture
def mock_discord_member():
    """Create a mock Discord member"""
    mock = MagicMock()
    mock.id = "user123"
    mock.name = "TestUser"
    mock.display_name = "Test User"
    return mock
