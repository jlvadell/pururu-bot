from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

import pytest
from hamcrest import assert_that, equal_to, has_length

from pururu.domain.entities.poll import Poll, PollReference, PollResolutionType
from pururu.domain.services.poll_system.poll_system_service import PollSystemService
from tests.test_domain.conftest import poll


@pytest.fixture
def mock_poll_repository():
    """Create a mock PollRepository"""
    return MagicMock()


@pytest.fixture
def mock_discord_service():
    """Create a mock DiscordService with async methods"""
    service = MagicMock()
    service.fetch_poll = AsyncMock()
    return service


@pytest.fixture
def mock_poll_resolution_factory():
    """Create a mock PollResolutionFactory"""
    return MagicMock()


@pytest.fixture
def service(mock_poll_repository, mock_discord_service, mock_poll_resolution_factory):
    """Create a PollSystemService instance"""
    return PollSystemService(
        mock_poll_repository,
        mock_discord_service,
        mock_poll_resolution_factory
    )


@pytest.mark.unit
def test_get_expired_polls_returns_all_expired_polls(service, mock_poll_repository):
    """Test get_expired_polls returns all expired polls from repository"""
    # Arrange
    expired_poll1 = PollReference(
        id="poll1",
        channel_id="channel1",
        expires_at=datetime(2025, 10, 1, 12, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE
    )
    expired_poll2 = PollReference(
        id="poll2",
        channel_id="channel2",
        expires_at=datetime(2025, 10, 1, 13, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE
    )
    mock_poll_repository.find_all_expired.return_value = [expired_poll1, expired_poll2]

    # Act
    result = service.get_expired_polls()

    # Assert
    mock_poll_repository.find_all_expired.assert_called_once()
    assert_that(result, has_length(2))
    assert_that(result[0], equal_to(expired_poll1))
    assert_that(result[1], equal_to(expired_poll2))


@pytest.mark.unit
def test_get_expired_polls_returns_empty_list_when_no_polls(service, mock_poll_repository):
    """Test get_expired_polls returns empty list when no expired polls"""
    # Arrange
    mock_poll_repository.get_expired_polls.return_value = []

    # Act
    result = service.get_expired_polls()

    # Assert
    mock_poll_repository.find_all_expired.assert_called_once()
    assert_that(result, has_length(0))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_finalize_poll_resolves_poll_successfully(
    service,
    mock_poll_repository,
    mock_discord_service,
    mock_poll_resolution_factory,
    poll
):
    """Test finalize_poll successfully fetches, resolves, and removes poll"""
    # Arrange
    poll_ref = PollReference(
        id=poll.id,
        channel_id=poll.channel_id,
        expires_at=poll.expires_at,
        resolution_type=poll.resolution_type
    )
    mock_poll_repository.find_by_id.return_value = poll_ref
    mock_discord_service.fetch_poll.return_value = poll

    mock_strategy = MagicMock()
    mock_strategy.resolve = AsyncMock()
    mock_poll_resolution_factory.get_strategy.return_value = mock_strategy

    # Act
    await service.finalize_poll(poll.id)

    # Assert
    mock_poll_repository.find_by_id.assert_called_once_with(poll.id)
    mock_discord_service.fetch_poll.assert_called_once_with(poll_ref)
    mock_poll_resolution_factory.get_strategy.assert_called_once_with(poll_ref.resolution_type)
    mock_strategy.resolve.assert_called_once_with(poll)
    mock_poll_repository.delete.assert_called_once_with(poll.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_finalize_poll_does_nothing_when_poll_not_found_in_repository(
    service,
    mock_poll_repository,
    mock_discord_service,
    mock_poll_resolution_factory
):
    """Test finalize_poll returns early when poll not found in repository"""
    # Arrange
    poll_id = "nonexistent_poll"
    mock_poll_repository.find_by_id.return_value = None

    # Act
    await service.finalize_poll(poll_id)

    # Assert
    mock_poll_repository.find_by_id.assert_called_once_with(poll_id)
    mock_discord_service.fetch_poll.assert_not_called()
    mock_poll_resolution_factory.get_strategy.assert_not_called()
    mock_poll_repository.remove_poll.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_finalize_poll_removes_poll_when_not_found_in_discord(
    service,
    mock_poll_repository,
    mock_discord_service,
    mock_poll_resolution_factory
):
    """Test finalize_poll removes poll from repository when not found in Discord"""
    # Arrange
    poll_ref = PollReference(
        id="poll123",
        channel_id="channel456",
        expires_at=datetime(2025, 10, 2, 12, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE
    )
    mock_poll_repository.find_by_id.return_value = poll_ref
    mock_discord_service.fetch_poll.return_value = None

    # Act
    await service.finalize_poll(poll_ref.id)

    # Assert
    mock_poll_repository.find_by_id.assert_called_once_with(poll_ref.id)
    mock_discord_service.fetch_poll.assert_called_once_with(poll_ref)
    mock_poll_resolution_factory.get_strategy.assert_not_called()
    mock_poll_repository.delete.assert_called_once_with(poll_ref.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_finalize_poll_uses_correct_resolution_strategy(
    service,
    mock_poll_repository,
    mock_discord_service,
    mock_poll_resolution_factory,
    poll
):
    """Test finalize_poll uses the correct resolution strategy based on poll type"""
    # Arrange
    poll_ref = PollReference(
        id=poll.id,
        channel_id=poll.channel_id,
        expires_at=poll.expires_at,
        resolution_type=PollResolutionType.SEND_MESSAGE
    )
    mock_poll_repository.find_by_id.return_value = poll_ref
    mock_discord_service.fetch_poll.return_value = poll

    mock_strategy = MagicMock()
    mock_strategy.resolve = AsyncMock()
    mock_poll_resolution_factory.get_strategy.return_value = mock_strategy

    # Act
    await service.finalize_poll(poll.id)

    # Assert
    mock_poll_resolution_factory.get_strategy.assert_called_once_with(PollResolutionType.SEND_MESSAGE)
    mock_strategy.resolve.assert_called_once_with(poll)

