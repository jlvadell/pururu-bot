from unittest.mock import MagicMock

import pytest
from hamcrest import assert_that, equal_to, none

from pururu.domain.services.season_service import SeasonService
from tests.test_domain.conftest import season


@pytest.fixture
def mock_season_repository():
    """Create a mock SeasonRepository"""
    return MagicMock()


@pytest.fixture
def service(mock_season_repository):
    """Create a SeasonService instance"""
    return SeasonService(mock_season_repository)


@pytest.mark.unit
def test_get_current_season_returns_season(service, mock_season_repository, season):
    """Test get_current_season returns current season from repository"""
    # Arrange
    mock_season_repository.get_current_season.return_value = season

    # Act
    result = service.get_current_season()

    # Assert
    mock_season_repository.get_current_season.assert_called_once()
    assert_that(result, equal_to(season))


@pytest.mark.unit
def test_get_current_season_returns_none(service, mock_season_repository):
    """Test get_current_season returns None when no active season"""
    # Arrange
    mock_season_repository.get_current_season.return_value = None

    # Act
    result = service.get_current_season()

    # Assert
    mock_season_repository.get_current_season.assert_called_once()
    assert_that(result, none())
