from unittest.mock import patch, AsyncMock, Mock

import discord
import pytest
from discord.app_commands import Command

from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot


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
    # Given
    bot_instance = set_up()
    guild = discord.Object(id=123456)
    command_mock = Mock()
    command_mock.name = 'testcommand'
    mock_sync.return_value = [command_mock]
    # When
    await bot_instance.setup_hook()
    # Then
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
    # Given
    discord_bot = set_up()
    # When
    await discord_bot.on_ready()
    # Then
    discord_bot.event_handler.handle_on_ready_event.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_on_voice_state_update_ok():
    """Test the on_voice_state_update event"""
    # Given
    discord_bot = set_up()
    member = Mock(spec=discord.Member)
    member.name = 'member'
    member.id = 123456
    before_state = Mock(spec=discord.VoiceState, channel=Mock())
    before_state.channel.name = 'before_state'
    after_state = Mock(spec=discord.VoiceState, channel=Mock())
    after_state.channel.name = 'after_state'
    # When
    await discord_bot.on_voice_state_update(member, before_state, after_state)
    # Then
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
    # Given
    discord_bot = set_up()
    discord_bot.setup_commands()

    ping_command: Command = next(filter(lambda x: x.name == 'ping', discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    # When
    await ping_command.callback(interaction=interaction)
    # Then
    interaction.response.send_message.assert_called_once_with('Pong! Pururu v1.0.0 is watching! :3')
