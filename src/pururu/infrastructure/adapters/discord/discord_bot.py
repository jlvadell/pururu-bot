import discord
from discord.ext import commands

from pururu.__version__ import get_version
from pururu.application.handlers.discord_event_handler import DiscordEventHandler
from pururu.common import logger
from pururu.config import settings
from pururu.infrastructure.adapters.discord.discord_ui_views import SessionInfoLayoutView
from pururu.infrastructure.exceptions import (DiscordChannelNotFoundException, DiscordMessageNotFoundException,
                                              DiscordUnExpectedException)


class PururuDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="/", intents=intents)
        self.logger = logger.get_logger(__name__)
        self.event_handler = None

    def set_event_handler(self, event_handler: DiscordEventHandler):
        # code smell: we should find a way to inject this dependency in the constructor
        # possible solution: create a new event bus with application events
        self.event_handler = event_handler

    async def setup_hook(self) -> None:
        self.setup_commands()
        guild = discord.Object(id=settings.discord.guild_id)
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        result = await self.tree.sync(guild=guild)
        self.logger.info("Commands synced successfully", extra={
            "guild_id": settings.discord.guild_id,
            "command_count": len(result),
            "commands": [x.name for x in result]
        })

    async def on_voice_state_update(self, member: discord.Member, before_state: discord.VoiceState,
                                    after_state: discord.VoiceState):
        before_name = before_state.channel.name if before_state.channel else None
        after_name = after_state.channel.name if after_state.channel else None
        self.logger.info(f"Voice state changed for member {member.name}, from {before_name} to {after_name}", extra={
            "member": member.name,
            "before_channel": before_name,
            "after_channel": after_name
        })
        self.event_handler.handle_on_voice_state_update_event(str(member.id), member.name, before_name, after_name)

    async def on_ready(self):
        self.logger.info("Pururu Discord Bot is ready!")
        self.event_handler.handle_on_ready_event()

    def setup_commands(self):
        self.logger.debug("Setting up commands...")

        @self.tree.command(
            name='ping',
            description='Sends a ping to Pururu'
        )
        async def ping_command(interaction: discord.Interaction):
            self.logger.info("Ping command received", extra={
                "user": interaction.user.name,
                "guild": interaction.guild.name if interaction.guild else None
            })
            await interaction.response.send_message(
                f"Pong! Pururu {get_version()} is watching! :3")

    async def send_session_info_view_message(self, channel_id: str, session) -> str:
        channel = self.get_channel(int(channel_id))
        if not channel:
            self.logger.error(f"Failed to send session info view to channel {channel_id}", extra={
                "channel_id": channel_id
            })
            raise DiscordChannelNotFoundException(f"Channel {channel_id} not found")
        try:
            player_id = int(session.get_first_joiner().player_id)
            discord_user = await self.fetch_user(player_id)
            avatar_url = discord_user.avatar.url
            view = SessionInfoLayoutView(session,
                                         on_session_type_change=self.event_handler.handle_session_type_change_modal_submit,
                                         on_attendance_edit=self.event_handler.handle_session_attendance_edit_modal_submit,
                                         thumbnail_url=avatar_url)
            message = await channel.send(view=view)
            return str(message.id)
        except Exception as e:
            self.logger.error(f"Failed to send session info view to channel {channel_id}",
                              extra={"session_id": session.id}, exc_info=True)
            raise DiscordUnExpectedException(f"Failed to send session info view to channel {channel_id}") from e

    async def edit_session_info_view_message(self, channel_id: str, message_id: str, session) -> None:
        channel = self.get_channel(int(channel_id))
        if not channel:
            self.logger.error(f"Failed to send session info view to channel {channel_id}", extra={
                "channel_id": channel_id
            })
            raise DiscordChannelNotFoundException(f"Channel {channel_id} not found")
        message = await channel.fetch_message(int(message_id))
        if not message:
            self.logger.error(f"Failed to fetch message {message_id} in channel {channel_id}", extra={
                "channel_id": channel_id,
                "message_id": message_id
            })
            raise DiscordMessageNotFoundException(f"Channel {channel_id} not found")
        try:
            player_id = int(session.get_last_joiner().player_id)
            discord_user = await self.fetch_user(player_id)
            avatar_url = discord_user.avatar.url
            view = SessionInfoLayoutView(session,
                                         on_session_type_change=self.event_handler.handle_session_type_change_modal_submit,
                                         on_attendance_edit=self.event_handler.handle_session_attendance_edit_modal_submit,
                                         thumbnail_url=avatar_url)
            await message.edit(view=view)
        except Exception:
            self.logger.error(f"Failed to edit session info view message {message_id} in channel {channel_id}",
                              extra={"session_id": session.id}, exc_info=True)
            raise DiscordUnExpectedException(
                f"Failed to edit session info view message {message_id} in channel {channel_id}")
