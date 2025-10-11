from unittest.mock import patch, AsyncMock, Mock, MagicMock

import discord
import pytest
from discord.app_commands import Command
from hamcrest import assert_that, equal_to

from pururu.domain.entities.session import Session
from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot
from pururu.infrastructure.adapters.discord.discord_ui_views import EditSessionTypeModal, EditAttendanceModal
from pururu.infrastructure.exceptions import (DiscordChannelNotFoundException, DiscordMessageNotFoundException,
                                              DiscordUnExpectedException)


@patch('pururu.application.handlers.discord_event_handler.DiscordEventHandler')
def set_up(discord_event_handler_mock):
    discord_bot = PururuDiscordBot()
    discord_bot.set_event_handler(discord_event_handler_mock)
    discord_bot.logger = Mock()
    return discord_bot


@patch('pururu.config.settings.discord.guild_id', 123456)
@pytest.mark.asyncio
@pytest.mark.unit
@patch.object(PururuDiscordBot, 'setup_commands', new_callable=AsyncMock)
@patch.object(discord.app_commands.CommandTree, 'clear_commands', new_callable=AsyncMock)
@patch.object(discord.app_commands.CommandTree, 'copy_global_to', new_callable=AsyncMock)
@patch.object(discord.app_commands.CommandTree, 'sync', new_callable=AsyncMock)
async def test_setup_hook(mock_sync, mock_copy_global, mock_clear_commands, mock_setup_commands):
    """Test the setup_hook method"""
    # Arrange
    bot_instance = set_up()
    guild = discord.Object(id=123456)
    command_mock = Mock()
    command_mock.name = 'testcommand'
    mock_sync.return_value = [command_mock]
    # Act
    await bot_instance.setup_hook()
    # Assert
    mock_setup_commands.assert_called_once()
    mock_clear_commands.assert_called_once_with(guild=guild)
    mock_copy_global.assert_called_once_with(guild=guild)
    mock_sync.assert_called_once_with(guild=guild)


# ------------------------------
# HOOK TESTS
# ------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_on_ready_ok():
    """Test the on_ready event"""
    # Arrange
    discord_bot = set_up()
    # Act
    await discord_bot.on_ready()
    # Assert
    discord_bot.event_handler.handle_on_ready_event.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_on_voice_state_update_ok():
    """Test the on_voice_state_update event"""
    # Arrange
    discord_bot = set_up()
    member = Mock(spec=discord.Member)
    member.name = 'member'
    member.id = 123456
    before_state = Mock(spec=discord.VoiceState, channel=Mock())
    before_state.channel.name = 'before_state'
    after_state = Mock(spec=discord.VoiceState, channel=Mock())
    after_state.channel.name = 'after_state'
    # Act
    await discord_bot.on_voice_state_update(member, before_state, after_state)
    # Assert
    discord_bot.event_handler.handle_on_voice_state_update_event.assert_called_once_with('123456', 'member',
                                                                                         'before_state',
                                                                                         'after_state')


# ------------------------------
# SLASH COMMAND TESTS
# ------------------------------

@patch('pururu.infrastructure.adapters.discord.discord_bot.get_version', return_value='v1.0.0')
@pytest.mark.asyncio
@pytest.mark.unit
async def test_ping_command_ok(get_Version_mock):
    """Test the ping command"""
    # Arrange
    discord_bot = set_up()
    discord_bot.setup_commands()

    ping_command: Command = next(filter(lambda x: x.name == 'ping', discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    # Act
    await ping_command.callback(interaction=interaction)
    # Assert
    interaction.response.send_message.assert_called_once_with('Pong! Pururu v1.0.0 is watching! :3')


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.infrastructure.adapters.discord.discord_bot.EditSessionTypeModal')
async def test_change_type_command_ok(modal_mock):
    """Test the type command session exists"""
    # Arrange
    session_mock = Mock(spec=Session, id="123456")
    modal_instance = Mock(spec=EditSessionTypeModal)
    modal_mock.return_value = modal_instance
    discord_bot = set_up()
    discord_bot.event_handler.handle_change_type_command.return_value = session_mock
    discord_bot.setup_commands()

    type_command: Command = next(filter(lambda x: x.name == 'type', discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    # Act
    await type_command.callback(interaction=interaction, session_id="123456")
    # Assert
    modal_mock.assert_called_once_with(session_mock, discord_bot.event_handler.handle_session_type_change_modal_submit)
    discord_bot.event_handler.handle_change_type_command.assert_called_once_with("123456")
    interaction.response.send_modal.assert_awaited_once_with(modal_instance)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_change_type_command_not_found():
    """Test the type command session not found"""
    # Arrange
    discord_bot = set_up()
    discord_bot.event_handler.handle_change_type_command.return_value = None
    discord_bot.setup_commands()

    type_command: Command = next(filter(lambda x: x.name == 'type', discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    # Act
    await type_command.callback(interaction=interaction, session_id="123456")
    # Assert
    discord_bot.event_handler.handle_change_type_command.assert_called_once_with("123456")
    interaction.response.send_message.assert_awaited_once()
    interaction.response.send_modal.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.infrastructure.adapters.discord.discord_bot.EditAttendanceModal')
async def test_edit_attendance_command_ok(modal_mock):
    """Test the attendance command session exists"""
    # Arrange
    session_mock = Mock(spec=Session, id="123456")
    modal_instance = Mock(spec=EditAttendanceModal)
    modal_mock.return_value = modal_instance
    discord_bot = set_up()
    discord_bot.event_handler.handle_edit_attendance_command.return_value = session_mock
    discord_bot.setup_commands()

    type_command: Command = next(filter(lambda x: x.name == 'attendance', discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    # Act
    await type_command.callback(interaction=interaction, session_id="123456")
    # Assert
    modal_mock.assert_called_once_with(session_mock,
                                       discord_bot.event_handler.handle_session_attendance_edit_modal_submit)
    discord_bot.event_handler.handle_edit_attendance_command.assert_called_once_with("123456")
    interaction.response.send_modal.assert_awaited_once_with(modal_instance)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_attendance_command_not_found():
    """Test the attendance command session not found"""
    # Arrange
    discord_bot = set_up()
    discord_bot.event_handler.handle_edit_attendance_command.return_value = None
    discord_bot.setup_commands()

    type_command: Command = next(filter(lambda x: x.name == 'attendance', discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    # Act
    await type_command.callback(interaction=interaction, session_id="123456")
    # Assert
    discord_bot.event_handler.handle_edit_attendance_command.assert_called_once_with("123456")
    interaction.response.send_message.assert_awaited_once()
    interaction.response.send_modal.assert_not_called()


# ------------------------------
# Others
# ------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_session_view_message_no_channel():
    """Test send_session_info_view_message raises DiscordChannelNotFoundException when channel is not found"""
    # Arrange
    channel_id = '999999'  # Non-existent channel ID
    session = Mock()

    discord_bot = set_up()

    # Act & Assert
    with pytest.raises(DiscordChannelNotFoundException):
        await discord_bot.send_session_info_view_message(channel_id, session)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_session_view_message_exception():
    """Test send_session_info_view_message raises DiscordUnExpectedException when something goes wrong"""
    # Arrange
    channel_id = '123456'
    session = Mock()
    session.get_first_joiner.return_value.player_id = '123456'

    discord_bot = set_up()
    discord_bot.get_channel = Mock(return_value=Mock())  # Mock channel found
    discord_bot.fetch_user = AsyncMock(side_effect=Exception("Test exception"))

    # Act & Assert
    with pytest.raises(DiscordUnExpectedException):
        await discord_bot.send_session_info_view_message(channel_id, session)


@pytest.mark.asyncio
@pytest.mark.unit
@patch('pururu.infrastructure.adapters.discord.discord_bot.SessionInfoLayoutView')
async def test_send_session_view_message_ok(mock_view_class):
    """Test send_session_info_view_message works correctly"""
    # Arrange
    channel_id = '123456'
    expected_message_id = 'message_123'
    session = Mock()
    session.get_first_joiner.return_value.player_id = '123456'

    discord_bot = set_up()

    mock_channel = AsyncMock()
    mock_channel.send = AsyncMock(return_value=Mock(id=expected_message_id))
    discord_bot.get_channel = Mock(return_value=mock_channel)

    mock_user = Mock()
    mock_user.avatar.url = 'http://avatar.url'
    discord_bot.fetch_user = AsyncMock(return_value=mock_user)

    mock_view = MagicMock()
    mock_view_class.return_value = mock_view

    # Act
    result = await discord_bot.send_session_info_view_message(channel_id, session)

    # Assert
    assert_that(result, equal_to(expected_message_id))
    mock_view_class.assert_called_once_with(
        session,
        on_session_type_change=discord_bot.event_handler.handle_session_type_change_modal_submit,
        on_attendance_edit=discord_bot.event_handler.handle_session_attendance_edit_modal_submit,
        thumbnail_url=mock_user.avatar.url
    )
    discord_bot.get_channel.assert_called_once_with(123456)
    discord_bot.fetch_user.assert_awaited_once_with(123456)
    mock_channel.send.assert_awaited_once_with(view=mock_view)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_edit_session_info_view_message_no_channel():
    """Test edit_session_info_view_message raises DiscordChannelNotFoundException when channel is not found"""
    # Arrange
    channel_id = '999999'  # Non-existent channel ID
    message_id = '123456'
    session = Mock()

    discord_bot = set_up()

    # Act & Assert
    with pytest.raises(DiscordChannelNotFoundException):
        await discord_bot.edit_session_info_view_message(channel_id, message_id, session)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_edit_session_info_view_message_no_message():
    """Test edit_session_info_view_message raises DiscordChannelNotFoundException Act message is not found"""
    # Arrange
    channel_id = '123456'
    message_id = '999999'  # Non-existent message ID
    session = Mock()

    discord_bot = set_up()

    mock_channel = AsyncMock()
    mock_channel.fetch_message = AsyncMock(return_value=None)  # Simulate message not found
    discord_bot.get_channel = Mock(return_value=mock_channel)

    # Act & Assert
    with pytest.raises(DiscordMessageNotFoundException):
        await discord_bot.edit_session_info_view_message(channel_id, message_id, session)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_edit_session_info_view_message_exception():
    """Test edit_session_info_view_message raises DiscordUnExpectedException when something goes wrong"""
    # Arrange
    channel_id = '123456'
    message_id = '789012'
    session = Mock()
    session.get_last_joiner.return_value.player_id = '123456'

    discord_bot = set_up()
    message_mock = AsyncMock(name="MessageMock")

    mock_channel = AsyncMock(name="MockChannel")
    mock_channel.fetch_message.return_value = message_mock  # Simulate message not found
    discord_bot.get_channel = Mock(return_value=mock_channel)

    discord_bot.fetch_user = AsyncMock(side_effect=Exception("Test exception"))

    # Act & Assert
    with pytest.raises(DiscordUnExpectedException):
        await discord_bot.edit_session_info_view_message(channel_id, message_id, session)


@pytest.mark.asyncio
@pytest.mark.unit
@patch('pururu.infrastructure.adapters.discord.discord_bot.SessionInfoLayoutView')
async def test_edit_session_info_view_message_ok(mock_view_class):
    """Test edit_session_info_view_message works correctly"""
    # Arrange
    channel_id = '123456'
    message_id = '789012'
    session = Mock()
    session.get_last_joiner.return_value.player_id = '123456'

    discord_bot = set_up()

    mock_message = AsyncMock()
    mock_message.edit = AsyncMock()

    mock_channel = AsyncMock()
    mock_channel.fetch_message = AsyncMock(return_value=mock_message)
    discord_bot.get_channel = Mock(return_value=mock_channel)

    mock_user = Mock()
    mock_user.avatar.url = 'http://avatar.url'
    discord_bot.fetch_user = AsyncMock(return_value=mock_user)

    mock_view = MagicMock()
    mock_view_class.return_value = mock_view

    # Act
    result = await discord_bot.edit_session_info_view_message(channel_id, message_id, session)

    # Assert
    mock_view_class.assert_called_once_with(
        session,
        on_session_type_change=discord_bot.event_handler.handle_session_type_change_modal_submit,
        on_attendance_edit=discord_bot.event_handler.handle_session_attendance_edit_modal_submit,
        thumbnail_url=mock_user.avatar.url
    )
    discord_bot.get_channel.assert_called_once_with(123456)
    mock_channel.fetch_message.assert_awaited_once_with(789012)
    discord_bot.fetch_user.assert_awaited_once_with(123456)
    mock_message.edit.assert_awaited_once_with(view=mock_view)
