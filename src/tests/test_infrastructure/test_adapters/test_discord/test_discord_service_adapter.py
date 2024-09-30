from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from hamcrest import assert_that, equal_to

from pururu.domain.entities import Message, Poll
from pururu.infrastructure.adapters.discord.discord_service_adapter import DiscordServiceAdapter
from pururu.domain.exceptions import DiscordServiceException
from tests.test_domain.test_entities import message, poll


@patch('pururu.config.GUILD_ID', 123456)
def set_up():
    mock_bot = AsyncMock(name='my_client_mock')
    mock_bot.guilds = [MagicMock(id=123456)]
    dc_service = DiscordServiceAdapter(mock_bot)
    return dc_service


@pytest.mark.asyncio
async def test_send_message_ok(message: Message):
    # Given
    dc_service = set_up()
    channel_mock = AsyncMock()
    dc_service.guild.get_channel.return_value = channel_mock
    message_id = 2222
    channel_mock.send.return_value = AsyncMock(id=message_id)
    # When
    result = await dc_service.send_message(message)
    # Then
    assert_that(result.channel_id, equal_to(message.channel_id))
    assert_that(result.content, equal_to(message.content))
    assert_that(result.message_id, equal_to(message_id))
    dc_service.guild.get_channel.assert_called_once_with(message.channel_id)
    channel_mock.send.assert_called_once_with(message.content)


@pytest.mark.asyncio
async def test_send_message_ko_channel_not_found(message: Message):
    # Given
    dc_service = set_up()
    dc_service.guild.get_channel.return_value = None
    # When
    with pytest.raises(DiscordServiceException) as exc_info:
        await dc_service.send_message(message)

    # Then
    dc_service.guild.get_channel.assert_called_once_with(message.channel_id)
    assert_that(exc_info.value.args[0], equal_to(f"Unable to send message, channel {message.channel_id} not found"))


@pytest.mark.asyncio
async def test_send_poll_ok(poll: Poll):
    # Given
    dc_service = set_up()
    channel_mock = AsyncMock()
    dc_service.guild.get_channel.return_value = channel_mock
    message_id = 2222
    message_mock = AsyncMock(id=message_id)
    channel_mock.send.return_value = message_mock
    message_mock.poll.expires_at = datetime(2023, 8, 10, 12)
    # When
    result = await dc_service.send_poll(poll)
    # Then
    assert_that(result.channel_id, equal_to(poll.channel_id))
    assert_that(result.answers, equal_to(poll.answers))
    assert_that(result.duration_hours, equal_to(poll.duration_hours))
    assert_that(result.allow_multiple, equal_to(poll.allow_multiple))
    assert_that(result.message_id, equal_to(message_id))
    assert_that(result.expires_at, equal_to(datetime(2023, 8, 10, 12)))
    dc_service.guild.get_channel.assert_called_once_with(poll.channel_id)
    channel_mock.send.assert_called_once()


@pytest.mark.asyncio
async def test_send_poll_ko_channel_not_found(poll: Poll):
    # Given
    dc_service = set_up()
    dc_service.guild.get_channel.return_value = None
    # When
    with pytest.raises(DiscordServiceException) as exc_info:
        await dc_service.send_poll(poll)

    # Then
    dc_service.guild.get_channel.assert_called_once_with(poll.channel_id)
    assert_that(exc_info.value.args[0], equal_to(f"Unable to send poll, channel {poll.channel_id} not found"))


@pytest.mark.asyncio
async def test_fetch_poll_ok(poll: Poll):
    # Given
    dc_service = set_up()
    channel_id = 1234
    poll_id = 5678
    channel_mock = AsyncMock(id=channel_id)
    message_mock = AsyncMock(id=poll_id)
    dc_service.guild.get_channel.return_value = channel_mock
    channel_mock.fetch_message.return_value = message_mock
    poll_mock = AsyncMock()
    message_mock.poll = poll_mock
    poll_mock.question = "poll question?"
    poll_mock.duration.hours = 1
    poll_mock.multiple = False
    poll_mock.expires_at = datetime(2023, 8, 10, 12)
    poll_mock.answers = [MagicMock(text="yes", count=1), MagicMock(text="no", count=2)]
    # When
    result = await dc_service.fetch_poll(channel_id, poll_id)
    # Then
    assert_that(result.channel_id, equal_to(channel_id))
    assert_that(result.answers, equal_to(poll.answers))
    assert_that(result.duration_hours, equal_to(poll.duration_hours))
    assert_that(result.allow_multiple, equal_to(poll.allow_multiple))
    assert_that(result.message_id, equal_to(poll_id))
    assert_that(result.results, equal_to({"yes": 1, "no": 2}))
    assert_that(result.expires_at, equal_to(datetime(2023, 8, 10, 12)))
    dc_service.guild.get_channel.assert_called_once_with(channel_id)
    channel_mock.fetch_message.assert_called_once_with(poll_id)


@pytest.mark.asyncio
async def test_fetch_poll_ko_channel_not_found():
    # Given
    channel_id = 1234
    poll_id = 5678
    dc_service = set_up()
    dc_service.guild.get_channel.return_value = None
    # When
    with pytest.raises(DiscordServiceException) as exc_info:
        await dc_service.fetch_poll(channel_id, poll_id)

    # Then
    dc_service.guild.get_channel.assert_called_once_with(channel_id)
    assert_that(exc_info.value.args[0], equal_to(f"Channel with id {channel_id} not found"))


@pytest.mark.asyncio
async def test_fetch_poll_ko_message_not_found():
    # Given
    channel_id = 1234
    poll_id = 5678
    dc_service = set_up()
    channel_mock = AsyncMock(id=channel_id)
    dc_service.guild.get_channel.return_value = channel_mock
    channel_mock.fetch_message.return_value = None
    # When
    with pytest.raises(DiscordServiceException) as exc_info:
        await dc_service.fetch_poll(channel_id, poll_id)

    # Then
    dc_service.guild.get_channel.assert_called_once_with(channel_id)
    channel_mock.fetch_message.assert_called_once_with(poll_id)
    assert_that(exc_info.value.args[0], equal_to(f"Poll with id {poll_id} not found in channel {channel_id}"))
