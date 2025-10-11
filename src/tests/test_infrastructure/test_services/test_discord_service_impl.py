from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from hamcrest import assert_that, equal_to, none, instance_of, is_

from pururu.domain.entities.poll import PollReference, Poll, PollResolutionType
from pururu.infrastructure.exceptions import InfrastructureException
from pururu.infrastructure.services.discord_service_impl import DiscordServiceImpl


@pytest.fixture
def mock_discord_bot():
    """Create a mock PururuDiscordBot"""
    return MagicMock()


@pytest.fixture
def service(mock_discord_bot):
    """Create a DiscordServiceImpl instance with mocked dependencies"""
    return DiscordServiceImpl(mock_discord_bot)


@pytest.fixture
def poll_reference():
    """Create a sample PollReference"""
    return PollReference(
        id="987654",
        channel_id="123456",
        expires_at=datetime(2025, 10, 2, 12, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_simple_message_success(service, mock_discord_bot):
    """Test send_simple_message successfully sends message and returns True"""
    # Arrange
    channel_id = "123456"
    content = "Test message content"
    mock_channel = AsyncMock()
    mock_sent_message = MagicMock()
    mock_sent_message.id = 999888
    mock_channel.send.return_value = mock_sent_message
    mock_discord_bot.get_channel.return_value = mock_channel

    # Act
    result = await service.send_simple_message(channel_id, content)

    # Assert
    assert_that(result, is_(True))
    mock_discord_bot.get_channel.assert_called_once_with(123456)
    mock_channel.send.assert_called_once_with("Test message content")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_simple_message_channel_not_found(service, mock_discord_bot):
    """Test send_simple_message returns False when channel is not found"""
    # Arrange
    channel_id = "123456"
    content = "Test message content"
    mock_discord_bot.get_channel.return_value = None

    # Act
    result = await service.send_simple_message(channel_id, content)

    # Assert
    assert_that(result, is_(False))
    mock_discord_bot.get_channel.assert_called_once_with(123456)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_poll_success(service, mock_discord_bot, poll_reference):
    """Test fetch_poll successfully retrieves and parses poll data"""
    # Arrange
    mock_channel = AsyncMock()
    mock_message = MagicMock()
    mock_poll = MagicMock()

    # Configure mock poll
    mock_poll.id = "987654"
    mock_poll.question = "What game should we play?"
    mock_poll.duration.total_seconds.return_value = 86400  # 24 hours
    mock_poll.multiple = False
    mock_poll.expires_at = datetime(2025, 10, 2, 12, 0, 0)

    # Configure poll answers
    answer1 = MagicMock()
    answer1.text = "Game A"
    answer1.vote_count = 5
    answer2 = MagicMock()
    answer2.text = "Game B"
    answer2.vote_count = 3
    mock_poll.answers = [answer1, answer2]

    mock_message.poll = mock_poll
    mock_channel.fetch_message.return_value = mock_message
    mock_discord_bot.get_channel.return_value = mock_channel

    # Act
    result = await service.fetch_poll(poll_reference)

    # Assert
    assert_that(result, instance_of(Poll))
    assert_that(result.id, equal_to("987654"))
    assert_that(result.channel_id, equal_to("123456"))
    assert_that(result.question, equal_to("What game should we play?"))
    assert_that(result.duration_hours, equal_to(24.0))
    assert_that(result.allow_multiple, equal_to(False))
    assert_that(result.expires_at, equal_to(datetime(2025, 10, 2, 12, 0, 0)))
    assert_that(result.answers, equal_to(["Game A", "Game B"]))
    assert_that(result.results, equal_to({"Game A": 5, "Game B": 3}))
    mock_discord_bot.get_channel.assert_called_once_with(123456)
    mock_channel.fetch_message.assert_called_once_with(987654)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_poll_channel_not_found(service, mock_discord_bot, poll_reference):
    """Test fetch_poll returns None when channel is not found"""
    # Arrange
    mock_discord_bot.get_channel.return_value = None

    # Act
    result = await service.fetch_poll(poll_reference)

    # Assert
    assert_that(result, none())
    mock_discord_bot.get_channel.assert_called_once_with(123456)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_poll_message_not_found(service, mock_discord_bot, poll_reference):
    """Test fetch_poll returns None when message is not found"""
    # Arrange
    mock_channel = AsyncMock()
    mock_channel.fetch_message.return_value = None
    mock_discord_bot.get_channel.return_value = mock_channel

    # Act
    result = await service.fetch_poll(poll_reference)

    # Assert
    assert_that(result, none())
    mock_discord_bot.get_channel.assert_called_once_with(123456)
    mock_channel.fetch_message.assert_called_once_with(987654)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_session_info_view_message(service, mock_discord_bot):
    """Test send_session_info_view_message calls the bot method and returns message ID"""
    # Arrange
    channel_id = "123456"
    session = MagicMock()
    expected_message_id = "message_123"
    mock_discord_bot.send_session_info_view_message = AsyncMock(return_value=expected_message_id)

    # Act
    result = await service.send_session_info_view_message(channel_id, session)

    # Assert
    assert_that(result, equal_to(expected_message_id))
    mock_discord_bot.send_session_info_view_message.assert_called_once_with(channel_id, session)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_session_info_view_message_handles_error(service, mock_discord_bot):
    """Test send_session_info_view_message handles infrastructure error and returns None"""
    # Arrange
    channel_id = "123456"
    session = MagicMock()
    mock_discord_bot.send_session_info_view_message = AsyncMock(side_effect=InfrastructureException("Test exception"))

    # Act
    result = await service.send_session_info_view_message(channel_id, session)

    # Assert
    assert_that(result, is_(None))
    mock_discord_bot.send_session_info_view_message.assert_called_once_with(channel_id, session)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_session_info_view_message(service, mock_discord_bot):
    """Test update_session_info_view_message calls the bot method"""
    # Arrange
    channel_id = "123456"
    message_id = "message_123"
    session = MagicMock()
    mock_discord_bot.edit_session_info_view_message = AsyncMock()

    # Act
    await service.update_session_info_view_message(channel_id, message_id, session)

    # Assert
    mock_discord_bot.edit_session_info_view_message.assert_called_once_with(channel_id, message_id, session)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_session_info_view_message_handle_error(service, mock_discord_bot):
    """Test update_session_info_view_message handles infrastructure exception"""
    # Arrange
    channel_id = "123456"
    message_id = "message_123"
    session = MagicMock()
    mock_discord_bot.edit_session_info_view_message = AsyncMock(side_effect=InfrastructureException("Test exception"))

    # Act
    await service.update_session_info_view_message(channel_id, message_id, session)

    # Assert
    mock_discord_bot.edit_session_info_view_message.assert_called_once_with(channel_id, message_id, session)
