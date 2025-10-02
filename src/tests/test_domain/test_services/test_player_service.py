from unittest.mock import MagicMock

import pytest
from hamcrest import assert_that, equal_to

from pururu.domain.entities.player import Player
from pururu.domain.services.player_service import PlayerService
from tests.test_domain.conftest import player


@pytest.fixture
def mock_player_repository():
    """Create a mock PlayerRepository"""
    return MagicMock()


@pytest.fixture
def service(mock_player_repository):
    """Create a PlayerService instance"""
    return PlayerService(mock_player_repository)


@pytest.mark.unit
def test_get_players_returns_all_players(service, mock_player_repository, player):
    """Test get_players returns all players from repository"""
    # Arrange
    player1 = Player(id="player1", name="Player One", birthday=player.birthday)
    player2 = Player(id="player2", name="Player Two", birthday=player.birthday)
    mock_player_repository.get_all.return_value = [player1, player2]

    # Act
    result = service.get_players()

    # Assert
    mock_player_repository.get_all.assert_called_once()
    assert_that(len(result), equal_to(2))
    assert_that(result[0], equal_to(player1))
    assert_that(result[1], equal_to(player2))


@pytest.mark.unit
def test_get_players_returns_empty_list(service, mock_player_repository):
    """Test get_players returns empty list when no players"""
    # Arrange
    mock_player_repository.get_all.return_value = []

    # Act
    result = service.get_players()

    # Assert
    mock_player_repository.get_all.assert_called_once()
    assert_that(len(result), equal_to(0))
