from unittest.mock import patch, MagicMock, Mock, AsyncMock, PropertyMock

import pytest
from discord import Member, VoiceState

from pururu.domain.entities import MemberStats
from pururu.interface.discord.discord_event_handlers import DiscordEventHandler
from tests.test_domain.test_entities import member_stats


@patch('discord.Client')
@patch('pururu.domain.services.pururu_service.PururuService')
@patch('discord.app_commands.CommandTree', MagicMock())
def set_up(pururu_service_mock, dc_client_mock):
    event_handler = DiscordEventHandler(dc_client_mock, pururu_service_mock)
    event_handler.dc_command_tree = AsyncMock()
    return event_handler

#------------------------------
# EVENT HANDLER TESTS
#------------------------------

@patch('pururu.config.GUILD_ID', 123456)
@pytest.mark.asyncio
async def test_on_ready_ok():
    # Given
    dc_event_handler = set_up()
    guild1 = AsyncMock(id=123456)
    guild1.name = 'guild1'
    guild2 = AsyncMock(id=654321)
    guild2.name = 'guild2'
    dc_event_handler.dc_client.guilds = [guild1, guild2]
    # When
    await dc_event_handler.on_ready()
    # Then
    dc_event_handler.dc_command_tree.clear_commands.assert_called_once_with(guild=guild1)
    dc_event_handler.dc_command_tree.copy_global_to.assert_called_once_with(guild=guild1)
    dc_event_handler.dc_command_tree.sync.assert_called_once_with(guild=guild1)

@pytest.mark.asyncio
async def test_on_voice_state_update_ok():
    # Given
    dc_event_handler = set_up()
    member = Mock(spec=Member)
    before_state = Mock(spec=VoiceState)
    after_state = Mock(spec=VoiceState)
    member.name = 'member'
    before_state.channel.name = 'before_state'
    after_state.channel.name = 'after_state'
    # When
    await dc_event_handler.on_voice_state_update(member, before_state, after_state)
    # Then
    dc_event_handler.pururu_service.handle_voice_state_update.assert_called_once_with('member', 'before_state', 'after_state')

#------------------------------
# SLASH COMMAND HANDLER TESTS
#------------------------------

@patch('pururu.config.APP_VERSION', '1.0.0')
@pytest.mark.asyncio
async def test_ping_command_ok():
    # Given
    dc_event_handler = set_up()
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    # When
    await dc_event_handler.ping_command.callback(self=dc_event_handler, interaction=interaction)
    # Then
    interaction.response.send_message.assert_called_once_with('Pong! Pururu v1.0.0 is watching! :3')

@pytest.mark.asyncio
async def test_stats_command_ok(member_stats: MemberStats):
    # Given
    dc_event_handler = set_up()
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user.name = 'user_name'
    interaction.user.mention = 'user_mention'
    dc_event_handler.pururu_service.retrieve_player_stats.return_value = member_stats
    # When
    await dc_event_handler.stats_command.callback(self=dc_event_handler, interaction=interaction)
    # Then
    interaction.response.defer.assert_called_once_with(ephemeral=True, thinking=True)
    dc_event_handler.pururu_service.retrieve_player_stats.assert_called_once_with('user_name')
    interaction.followup.send.assert_called_once_with("Hola user_mention! Estos son tus Stats:\n"
                                                              +member_stats.as_message())