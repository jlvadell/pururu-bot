from unittest.mock import patch, AsyncMock, Mock

import discord
import pytest
from discord.app_commands import Command

from pururu.domain.entities import MemberStats
from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot
from tests.test_domain.test_entities import member_stats


@patch('pururu.application.services.pururu_handler.PururuHandler')
def set_up(pururu_handler_mock):
    discord_bot = PururuDiscordBot(pururu_handler_mock)
    discord_bot.logger = Mock()
    return discord_bot


@patch('pururu.config.GUILD_ID', 123456)
@pytest.mark.asyncio
@patch.object(PururuDiscordBot, 'setup_commands', new_callable=AsyncMock)
@patch.object(discord.app_commands.CommandTree, 'clear_commands', new_callable=AsyncMock)
@patch.object(discord.app_commands.CommandTree, 'copy_global_to', new_callable=AsyncMock)
@patch.object(discord.app_commands.CommandTree, 'sync', new_callable=AsyncMock)
async def test_setup_hook(mock_sync, mock_copy_global, mock_clear_commands, mock_setup_commands):
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
# EVENT HANDLER TESTS
# ------------------------------

@pytest.mark.asyncio
async def test_on_ready_ok():
    # Given
    discord_bot = set_up()
    # When
    await discord_bot.on_ready()
    # Then
    discord_bot.logger.info.assert_called_once()


@pytest.mark.asyncio
async def test_on_voice_state_update_ok():
    # Given
    discord_bot = set_up()
    member = Mock(spec=discord.Member)
    member.name = 'member'
    before_state = Mock(spec=discord.VoiceState, channel=Mock())
    before_state.channel.name = 'before_state'
    after_state = Mock(spec=discord.VoiceState, channel=Mock())
    after_state.channel.name = 'after_state'
    # When
    await discord_bot.on_voice_state_update(member, before_state, after_state)
    # Then
    discord_bot.pururu_handler.handle_voice_state_update_dc_event.assert_called_once_with('member', 'before_state',
                                                                                          'after_state')


# ------------------------------
# SLASH COMMAND HANDLER TESTS
# ------------------------------

@patch('pururu.config.PING_MESSAGE', None)
@patch('pururu.config.APP_VERSION', '1.0.0')
@pytest.mark.asyncio
async def test_ping_command_ok():
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


@patch('pururu.config.PING_MESSAGE', 'Something')
@patch('pururu.config.APP_VERSION', '1.0.0')
@pytest.mark.asyncio
async def test_ping_command_ok():
    # Given
    discord_bot = set_up()
    discord_bot.setup_commands()

    ping_command: Command = next(filter(lambda x: x.name == 'ping', discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    # When
    await ping_command.callback(interaction=interaction)
    # Then
    interaction.response.send_message.assert_called_once_with('Pong! Pururu v1.0.0 is watching! :3\nSomething')


@pytest.mark.asyncio
async def test_stats_command_ok(member_stats: MemberStats):
    # Given
    discord_bot = set_up()
    discord_bot.setup_commands()
    stats_command: Command = next(filter(lambda x: x.name == 'stats', discord_bot.tree.get_commands()))
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user.name = 'user_name'
    interaction.user.mention = 'user_mention'
    discord_bot.pururu_handler.retrieve_player_stats.return_value = member_stats
    # When
    await stats_command.callback(interaction=interaction)
    # Then
    interaction.response.defer.assert_called_once_with(ephemeral=True, thinking=True)
    discord_bot.pururu_handler.retrieve_player_stats.assert_called_once_with('user_name')
    interaction.followup.send.assert_called_once_with("Hola user_mention! Estos son tus Stats:\n"
                                                      + member_stats.as_message())
