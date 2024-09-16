from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from hamcrest import assert_that, equal_to

from pururu.domain.entities import Message
from pururu.infrastructure.adapters.discord.discord_service_adapter import DiscordServiceAdapter

from tests.test_domain.test_entities import message


@patch('pururu.config.GUILD_ID', 123456)
@patch('discord.Client')
def set_up(dc_client_mock):
    mock_client = AsyncMock(name='my_client_mock')
    mock_client.guilds = [MagicMock(id=123456)]
    dc_client_mock.return_value = mock_client
    dc_service = DiscordServiceAdapter()
    return dc_service


def test_get_client_ok():
    # Given
    dc_service = set_up()
    # When
    client = dc_service.get_client()
    # Then
    assert_that(client, equal_to(dc_service.client))


@pytest.mark.asyncio
async def test_send_message_ok(message: Message):
    # Given
    dc_service = set_up()
    response_message = AsyncMock(id=2222)
    text_channel = AsyncMock(id=123456, send=AsyncMock(return_value=response_message))
    dc_service.guild.text_channels = [text_channel]
    expected_message = Message(content=message.content, channel_id=message.channel_id)
    expected_message.message_id = 2222
    # When
    result = await dc_service.send_message(message)
    # Then
    assert_that(result.channel_id, equal_to(expected_message.channel_id))
    assert_that(result.message_id, equal_to(expected_message.message_id))
    assert_that(result.content, equal_to(expected_message.content))
    text_channel.send.assert_called_once_with(message.content)
