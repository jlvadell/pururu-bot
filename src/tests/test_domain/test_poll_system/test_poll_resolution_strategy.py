from unittest.mock import AsyncMock

import pytest
from hamcrest import assert_that

from pururu.domain.entities import Poll, Message
from pururu.domain.poll_system.poll_resolution_strategy import SendMessagePollResolution
from tests.test_domain.test_entities import poll


@pytest.mark.asyncio
async def test_send_message_strategy_resolve(poll: Poll):
    # Given
    poll_resolution_strategy = SendMessagePollResolution(AsyncMock())
    expected_message = f"{poll.question}\nOpción/es ganadoras: {poll.get_winners()}"
    poll_resolution_strategy.discord_service.send_message.return_value = Message(expected_message, poll.channel_id)
    # When
    result: Message = await poll_resolution_strategy.resolve(poll)
    # Then
    poll_resolution_strategy.discord_service.send_message.assert_called_once()
    message = poll_resolution_strategy.discord_service.send_message.call_args[0][0]
    assert_that(message.content, expected_message)
    assert_that(result.content, expected_message)
    assert_that(result.channel_id, poll.channel_id)
