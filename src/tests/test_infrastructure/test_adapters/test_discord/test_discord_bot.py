from unittest.mock import patch, AsyncMock, Mock, MagicMock

import discord
import pytest
from discord.app_commands import Command
from hamcrest import assert_that, equal_to

from pururu.domain.entities.session import Session
from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot
from pururu.infrastructure.adapters.discord.discord_ui_views import (EditSessionTypeModal, EditAttendanceModal,
                                                                     RepairAttendanceModal)
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
@patch('pururu.infrastructure.adapters.discord.discord_bot.logger')
async def test_on_ready_ok(mock_logger):
    """Test the on_ready event sets trace context"""
    # Arrange
    discord_bot = set_up()
    mock_logger.generate_trace_id.return_value = "test_trace_123"
    mock_logger.set_trace_context = Mock()
    
    # Act
    await discord_bot.on_ready()
    
    # Assert
    mock_logger.generate_trace_id.assert_called_once()
    mock_logger.set_trace_context.assert_called_once_with("test_trace_123")
    discord_bot.event_handler.handle_on_ready_event.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
@patch('pururu.infrastructure.adapters.discord.discord_bot.logger')
async def test_on_voice_state_update_ok(mock_logger):
    """Test the on_voice_state_update event sets trace context"""
    # Arrange
    discord_bot = set_up()
    mock_logger.generate_trace_id.return_value = "test_trace_voice_456"
    mock_logger.set_trace_context = Mock()
    
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
    mock_logger.generate_trace_id.assert_called_once()
    mock_logger.set_trace_context.assert_called_once_with("test_trace_voice_456")
    discord_bot.event_handler.handle_on_voice_state_update_event.assert_called_once_with('123456', 'member',
                                                                                         'before_state',
                                                                                         'after_state')


@pytest.mark.asyncio
@pytest.mark.unit
@patch('pururu.infrastructure.adapters.discord.discord_bot.extract_playing_game_name')
async def test_on_presence_update_reports_new_game_when_in_voice(mock_extract):
    discord_bot = set_up()
    mock_extract.side_effect = ["League of Legends", None]
    after = Mock(spec=discord.Member)
    after.id = 123456
    after.name = "member"
    after.voice = Mock(channel=Mock())
    after.activities = ()
    before = Mock(spec=discord.Member)
    before.activities = ()

    await discord_bot.on_presence_update(before, after)

    discord_bot.event_handler.handle_player_game_activity_event.assert_called_once_with(
        "123456", "member", "League of Legends")


@pytest.mark.asyncio
@pytest.mark.unit
@patch('pururu.infrastructure.adapters.discord.discord_bot.extract_playing_game_name')
async def test_on_presence_update_ignores_members_not_in_voice(mock_extract):
    discord_bot = set_up()
    after = Mock(spec=discord.Member)
    after.voice = None

    await discord_bot.on_presence_update(Mock(), after)

    mock_extract.assert_not_called()
    discord_bot.event_handler.handle_player_game_activity_event.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
@patch('pururu.infrastructure.adapters.discord.discord_bot.extract_playing_game_name')
async def test_on_presence_update_ignores_unchanged_game(mock_extract):
    discord_bot = set_up()
    mock_extract.return_value = "League of Legends"
    after = Mock(spec=discord.Member)
    after.voice = Mock(channel=Mock())
    after.activities = ()
    before = Mock(spec=discord.Member)
    before.activities = ()

    await discord_bot.on_presence_update(before, after)

    discord_bot.event_handler.handle_player_game_activity_event.assert_not_called()


@pytest.mark.unit
@patch('pururu.infrastructure.adapters.discord.discord_bot.settings')
@patch('pururu.infrastructure.adapters.discord.discord_bot.extract_playing_game_name')
def test_scan_voice_games_reports_playing_members(mock_extract, mock_settings):
    mock_settings.discord.guild_id = 123
    discord_bot = set_up()
    playing_member = Mock()
    playing_member.bot = False
    playing_member.voice = Mock(channel=Mock())
    playing_member.id = 111
    playing_member.name = "p1"
    bot_member = Mock(bot=True, voice=Mock(channel=Mock()))
    offline = Mock(bot=False, voice=None)
    guild = Mock()
    guild.members = [playing_member, bot_member, offline]
    discord_bot.get_guild = Mock(return_value=guild)
    mock_extract.return_value = "League of Legends"

    discord_bot._scan_voice_games()

    discord_bot.event_handler.handle_player_game_activity_event.assert_called_once_with(
        "111", "p1", "League of Legends")


# ------------------------------
# SLASH COMMAND TESTS
# ------------------------------

@patch('pururu.infrastructure.adapters.discord.discord_bot.logger')
@patch('pururu.infrastructure.adapters.discord.discord_bot.get_version', return_value='v1.0.0')
@pytest.mark.asyncio
@pytest.mark.unit
async def test_ping_command_ok(get_Version_mock, mock_logger):
    """Test the ping command sets trace context"""
    # Arrange
    discord_bot = set_up()
    mock_logger.generate_trace_id.return_value = "test_trace_ping_789"
    mock_logger.set_trace_context = Mock()
    discord_bot.setup_commands()

    ping_command: Command = next(filter(lambda x: x.name == 'ping', discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    
    # Act
    await ping_command.callback(interaction=interaction)
    
    # Assert
    mock_logger.generate_trace_id.assert_called_once()
    mock_logger.set_trace_context.assert_called_once_with("test_trace_ping_789")
    interaction.response.send_message.assert_called_once_with('Pong! Pururu v1.0.0 is watching! :3')


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.infrastructure.adapters.discord.discord_bot.logger')
@patch('pururu.infrastructure.adapters.discord.discord_bot.EditSessionTypeModal')
async def test_change_type_command_ok(modal_mock, mock_logger):
    """Test the type command sets trace context and handles session"""
    # Arrange
    session_mock = Mock(spec=Session, id="123456")
    mock_logger.generate_trace_id.return_value = "test_trace_type_111"
    mock_logger.set_trace_context = Mock()
    
    discord_bot = set_up()
    discord_bot.event_handler.handle_change_type_command.return_value = session_mock
    discord_bot.setup_commands()

    type_command: Command = next(filter(lambda x: x.name == 'type', discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    
    # Act
    await type_command.callback(interaction=interaction, session_id="123456")
    
    # Assert
    mock_logger.generate_trace_id.assert_called_once()
    mock_logger.set_trace_context.assert_called_once_with("test_trace_type_111")
    discord_bot.event_handler.handle_change_type_command.assert_called_once_with("123456")
    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()


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
    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.infrastructure.adapters.discord.discord_bot.logger')
@patch('pururu.infrastructure.adapters.discord.discord_bot.EditAttendanceModal')
async def test_edit_attendance_command_ok(modal_mock, mock_logger):
    """Test the attendance command sets trace context and handles session"""
    # Arrange
    session_mock = Mock(spec=Session, id="123456")
    mock_logger.generate_trace_id.return_value = "test_trace_attendance_222"
    mock_logger.set_trace_context = Mock()
    
    discord_bot = set_up()
    discord_bot.event_handler.handle_edit_attendance_command.return_value = session_mock
    discord_bot.setup_commands()

    type_command: Command = next(filter(lambda x: x.name == 'attendance', discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    
    # Act
    await type_command.callback(interaction=interaction, session_id="123456")
    
    # Assert
    mock_logger.generate_trace_id.assert_called_once()
    mock_logger.set_trace_context.assert_called_once_with("test_trace_attendance_222")
    discord_bot.event_handler.handle_edit_attendance_command.assert_called_once_with("123456")
    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()


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
    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.infrastructure.adapters.discord.discord_bot.RepairAttendanceModal')
async def test_repair_attendance_command_opens_repair_flow(modal_mock):
    session_mock = Mock(spec=Session, id="123456")
    session_mock.is_concluded.return_value = True
    session_mock.get_absent_players.return_value = [Mock()]
    discord_bot = set_up()
    discord_bot.event_handler.handle_repair_attendance_command.return_value = session_mock
    discord_bot.setup_commands()
    command: Command = next(filter(lambda item: item.name == 'repair-attendance',
                                    discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()

    await command.callback(interaction=interaction, session_id="123456")

    discord_bot.event_handler.handle_repair_attendance_command.assert_called_once_with("123456")
    modal_mock.assert_called_once_with(
        session_mock, discord_bot.event_handler.handle_session_attendance_repair_modal_submit)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.followup.send.assert_awaited_once()


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
@patch('pururu.infrastructure.adapters.discord.discord_bot.logger')
@patch('pururu.infrastructure.adapters.discord.discord_bot.SessionInfoLayoutView')
async def test_send_session_view_message_ok(mock_view_class, mock_logger):
    """Test send_session_info_view_message sets trace context and works correctly"""
    # Arrange
    channel_id = '123456'
    expected_message_id = 'message_123'
    session = Mock()
    session.get_first_joiner.return_value.player_id = '123456'
    mock_logger.generate_trace_id.return_value = "test_trace_send_333"
    mock_logger.set_trace_context = Mock()

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
    mock_logger.generate_trace_id.assert_called_once()
    mock_logger.set_trace_context.assert_called_once_with("test_trace_send_333")
    assert_that(result, equal_to(expected_message_id))
    mock_view_class.assert_called_once_with(
        session,
        on_session_type_change=discord_bot.event_handler.handle_session_type_change_modal_submit,
        on_attendance_edit=discord_bot.event_handler.handle_session_attendance_edit_modal_submit,
        on_session_game_edit=discord_bot.event_handler.handle_session_game_edit_modal_submit,
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
@patch('pururu.infrastructure.adapters.discord.discord_bot.logger')
@patch('pururu.infrastructure.adapters.discord.discord_bot.SessionInfoLayoutView')
async def test_edit_session_info_view_message_ok(mock_view_class, mock_logger):
    """Test edit_session_info_view_message sets trace context and works correctly"""
    # Arrange
    channel_id = '123456'
    message_id = '789012'
    session = Mock()
    session.get_last_joiner.return_value.player_id = '123456'
    mock_logger.generate_trace_id.return_value = "test_trace_edit_444"
    mock_logger.set_trace_context = Mock()

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
    mock_logger.generate_trace_id.assert_called_once()
    mock_logger.set_trace_context.assert_called_once_with("test_trace_edit_444")
    mock_view_class.assert_called_once_with(
        session,
        on_session_type_change=discord_bot.event_handler.handle_session_type_change_modal_submit,
        on_attendance_edit=discord_bot.event_handler.handle_session_attendance_edit_modal_submit,
        on_session_game_edit=discord_bot.event_handler.handle_session_game_edit_modal_submit,
        thumbnail_url=mock_user.avatar.url
    )
    discord_bot.get_channel.assert_called_once_with(123456)
    mock_channel.fetch_message.assert_awaited_once_with(789012)
    discord_bot.fetch_user.assert_awaited_once_with(123456)
    mock_message.edit.assert_awaited_once_with(view=mock_view)
