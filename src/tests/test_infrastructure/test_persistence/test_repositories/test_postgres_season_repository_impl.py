from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, equal_to, none

from pururu.infrastructure.adapters.postgres.entities import SeasonRecord
from pururu.infrastructure.persistence.repositories.postgres_season_repository_impl import PostgresSeasonRepositoryImpl
from tests.test_domain.conftest import season


@pytest.fixture
def mock_engine():
    """Create a mock PostgresDBEngine"""
    mock = MagicMock()
    mock.get_engine.return_value = MagicMock()
    return mock


@pytest.fixture
def repository(mock_engine):
    """Create a PostgresSeasonRepositoryImpl instance"""
    return PostgresSeasonRepositoryImpl(mock_engine)


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_season_repository_impl.Session')
@patch('pururu.infrastructure.persistence.repositories.postgres_season_repository_impl.PostgresMapper')
def test_get_current_season_returns_season(mock_mapper, mock_session_class, repository, season):
    """Test get_current_season returns season with no end_date"""
    # Arrange
    mock_session_context = MagicMock()
    mock_session_class.return_value.__enter__.return_value = mock_session_context

    mock_record = MagicMock(spec=SeasonRecord)
    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = mock_record
    mock_mapper.map_record_to_season.return_value = season

    # Act
    result = repository.get_current_season()

    # Assert
    mock_mapper.map_record_to_season.assert_called_once_with(mock_record)
    assert_that(result, equal_to(season))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_season_repository_impl.Session')
def test_get_current_season_returns_none(mock_session_class, repository):
    """Test get_current_season returns None when no active season"""
    # Arrange
    mock_session_context = MagicMock()
    mock_session_class.return_value.__enter__.return_value = mock_session_context

    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = None

    # Act
    result = repository.get_current_season()

    # Assert
    assert_that(result, none())
