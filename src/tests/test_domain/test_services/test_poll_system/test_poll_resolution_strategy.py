from unittest.mock import MagicMock, AsyncMock

import pytest

from pururu.domain.services.poll_system.poll_resolution_strategy import SendMessagePollResolution
from tests.test_domain.conftest import poll


@pytest.fixture
def mock_discord_service():
    """Create a mock DiscordService with async methods"""
    service = MagicMock()
    service.send_simple_message = AsyncMock()
    return service


@pytest.fixture
def strategy(mock_discord_service):
    """Create a SendMessagePollResolution instance"""
    return SendMessagePollResolution(mock_discord_service)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_sends_message_with_poll_results(strategy, mock_discord_service, poll):
    """Test resolve sends a message to Discord with poll question and winners"""
    # Arrange
    mock_discord_service.send_simple_message.return_value = True
    expected_message = f"{poll.question}\nResults: {poll.get_winners()}"

    # Act
    await strategy.resolve(poll)

    # Assert
    mock_discord_service.send_simple_message.assert_called_once_with(
        poll.channel_id,
        expected_message
    )
