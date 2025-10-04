from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, equal_to, none

from pururu.domain.entities.poll import PollReference, PollResolutionType
from pururu.infrastructure.adapters.postgres.entities import PollRecord
from pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl import PostgresPollRepositoryImpl


@pytest.fixture
def mock_engine():
    """Create a mock PostgresDBEngine"""
    mock = MagicMock()
    mock.get_engine.return_value = MagicMock()
    return mock


@pytest.fixture
def repository(mock_engine):
    """Create a PostgresPollRepositoryImpl instance"""
    return PostgresPollRepositoryImpl(mock_engine)


@pytest.fixture
def poll_reference():
    """Create a sample PollReference"""
    return PollReference(
        id="poll123",
        channel_id="channel456",
        expires_at=datetime(2025, 10, 2, 12, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE
    )


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl.Session')
@patch('pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl.PostgresMapper')
def test_save_creates_poll(mock_mapper, mock_session_class, repository, poll_reference):
    """Test save creates a new poll in database"""
    # Arrange
    mock_session_context = MagicMock()
    mock_session_class.return_value.__enter__.return_value = mock_session_context

    mock_record = MagicMock(spec=PollRecord)
    mock_mapper.map_poll_to_record.return_value = mock_record
    mock_mapper.map_record_to_poll.return_value = poll_reference

    # Act
    result = repository.save(poll_reference)

    # Assert
    mock_mapper.map_poll_to_record.assert_called_once_with(poll_reference)
    mock_session_context.add.assert_called_once_with(mock_record)
    mock_session_context.commit.assert_called_once()
    mock_session_context.refresh.assert_called_once_with(mock_record)
    mock_mapper.map_record_to_poll.assert_called_once_with(mock_record)
    assert_that(result, equal_to(poll_reference))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl.Session')
def test_delete_poll_success(mock_session_class, repository):
    """Test delete removes poll and returns True"""
    # Arrange
    mock_session_context = MagicMock()
    mock_session_class.return_value.__enter__.return_value = mock_session_context

    mock_record = MagicMock(spec=PollRecord)
    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = mock_record

    # Act
    result = repository.delete("poll123")

    # Assert
    mock_session_context.delete.assert_called_once_with(mock_record)
    mock_session_context.commit.assert_called_once()
    assert_that(result, equal_to(True))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl.Session')
def test_delete_poll_not_found(mock_session_class, repository):
    """Test delete returns False when poll not found"""
    # Arrange
    mock_session_context = MagicMock()
    mock_session_class.return_value.__enter__.return_value = mock_session_context

    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = None

    # Act
    result = repository.delete("nonexistent")

    # Assert
    mock_session_context.delete.assert_not_called()
    mock_session_context.commit.assert_not_called()
    assert_that(result, equal_to(False))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl.Session')
@patch('pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl.PostgresMapper')
def test_find_by_id_returns_poll(mock_mapper, mock_session_class, repository, poll_reference):
    """Test find_by_id returns poll when found"""
    # Arrange
    mock_session_context = MagicMock()
    mock_session_class.return_value.__enter__.return_value = mock_session_context

    mock_record = MagicMock(spec=PollRecord)
    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = mock_record
    mock_mapper.map_record_to_poll.return_value = poll_reference

    # Act
    result = repository.find_by_id("poll123")

    # Assert
    mock_mapper.map_record_to_poll.assert_called_once_with(mock_record)
    assert_that(result, equal_to(poll_reference))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl.Session')
def test_find_by_id_returns_none(mock_session_class, repository):
    """Test find_by_id returns None when not found"""
    # Arrange
    mock_session_context = MagicMock()
    mock_session_class.return_value.__enter__.return_value = mock_session_context

    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = None

    # Act
    result = repository.find_by_id("nonexistent")

    # Assert
    assert_that(result, none())


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl.Session')
@patch('pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl.PostgresMapper')
def test_find_all_expired_returns_polls(mock_mapper, mock_session_class, repository):
    """Test find_all_expired returns all expired polls"""
    # Arrange
    mock_session_context = MagicMock()
    mock_session_class.return_value.__enter__.return_value = mock_session_context

    mock_record1 = MagicMock(spec=PollRecord)
    mock_record2 = MagicMock(spec=PollRecord)
    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.all.return_value = [mock_record1, mock_record2]

    poll1 = PollReference(
        id="poll1",
        channel_id="channel1",
        expires_at=datetime(2025, 10, 1, 10, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE
    )
    poll2 = PollReference(
        id="poll2",
        channel_id="channel2",
        expires_at=datetime(2025, 10, 1, 11, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE
    )
    mock_mapper.map_record_to_poll.side_effect = [poll1, poll2]

    # Act
    result = repository.find_all_expired()

    # Assert
    assert_that(len(result), equal_to(2))
    assert_that(result[0], equal_to(poll1))
    assert_that(result[1], equal_to(poll2))
    assert_that(mock_mapper.map_record_to_poll.call_count, equal_to(2))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl.Session')
def test_find_all_expired_returns_empty_list(mock_session_class, repository):
    """Test find_all_expired returns empty list when no expired polls"""
    # Arrange
    mock_session_context = MagicMock()
    mock_session_class.return_value.__enter__.return_value = mock_session_context

    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.all.return_value = []

    # Act
    result = repository.find_all_expired()

    # Assert
    assert_that(len(result), equal_to(0))
