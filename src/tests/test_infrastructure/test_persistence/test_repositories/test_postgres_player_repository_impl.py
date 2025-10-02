from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, equal_to

from pururu.domain.entities.player import Player
from pururu.infrastructure.adapters.postgres.entities import PlayerRecord
from pururu.infrastructure.persistence.repositories.postgres_player_repository_impl import PostgresPlayerRepositoryImpl
from tests.test_domain.conftest import player


@pytest.fixture
def mock_engine():
    """Create a mock PostgresDBEngine"""
    mock = MagicMock()
    mock.get_engine.return_value = MagicMock()
    return mock


@pytest.fixture
def repository(mock_engine):
    """Create a PostgresPlayerRepositoryImpl instance"""
    return PostgresPlayerRepositoryImpl(mock_engine)


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_player_repository_impl.Session')
@patch('pururu.infrastructure.persistence.repositories.postgres_player_repository_impl.PostgresMapper')
def test_get_all_returns_all_players(mock_mapper, mock_session_class, repository, player):
    """Test get_all returns all players from database"""
    # Arrange
    mock_session_context = MagicMock()
    mock_session_class.return_value.__enter__.return_value = mock_session_context

    mock_record1 = MagicMock(spec=PlayerRecord)
    mock_record2 = MagicMock(spec=PlayerRecord)
    mock_query = mock_session_context.query.return_value
    mock_query.all.return_value = [mock_record1, mock_record2]

    player1 = Player(id="player1", name="Player One", birthday=player.birthday)
    player2 = Player(id="player2", name="Player Two", birthday=player.birthday)
    mock_mapper.map_record_to_player.side_effect = [player1, player2]

    # Act
    result = repository.get_all()

    # Assert
    assert_that(len(result), equal_to(2))
    assert_that(result[0], equal_to(player1))
    assert_that(result[1], equal_to(player2))
    assert_that(mock_mapper.map_record_to_player.call_count, equal_to(2))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_player_repository_impl.Session')
def test_get_all_returns_empty_list(mock_session_class, repository):
    """Test get_all returns empty list when no players"""
    # Arrange
    mock_session_context = MagicMock()
    mock_session_class.return_value.__enter__.return_value = mock_session_context

    mock_query = mock_session_context.query.return_value
    mock_query.all.return_value = []

    # Act
    result = repository.get_all()

    # Assert
    assert_that(len(result), equal_to(0))
