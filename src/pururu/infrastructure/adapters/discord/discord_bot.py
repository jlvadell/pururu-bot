import asyncio

import discord
from discord.ext import commands

from pururu.__version__ import get_version
from pururu.application.handlers.discord_event_handler import DiscordEventHandler
from pururu.common import logger
from pururu.config import settings
from pururu.infrastructure.adapters.discord.discord_game_activity import extract_playing_game_name
from pururu.infrastructure.adapters.discord.discord_ui_views import SessionInfoLayoutView, EditSessionTypeModal, \
    EditAttendanceModal, RepairAttendanceModal
from pururu.infrastructure.exceptions import (DiscordChannelNotFoundException, DiscordMessageNotFoundException,
                                              DiscordUnExpectedException)


class PururuDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        # Privileged intents: required to read the game a member is playing while in a voice call.
        intents.members = True
        intents.presences = True
        super().__init__(command_prefix="/", intents=intents)
        self.logger = logger.get_logger(__name__)
        self.event_handler: DiscordEventHandler | None = None

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
        # Set trace context for this voice state update
        trace_id = logger.generate_trace_id()
        logger.set_trace_context(trace_id)
        
        before_name = before_state.channel.name if before_state.channel else None
        after_name = after_state.channel.name if after_state.channel else None
        self.logger.info(f"Voice state changed for member {member.name}, from {before_name} to {after_name}", extra={
            "member": member.name,
            "before_channel": before_name,
            "after_channel": after_name
        })
        self.event_handler.handle_on_voice_state_update_event(str(member.id), member.name, before_name, after_name)

    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        trace_id = logger.generate_trace_id()
        logger.set_trace_context(trace_id)
        in_voice = after.voice is not None and after.voice.channel is not None
        if not in_voice:
            return
        after_game = extract_playing_game_name(after.activities)
        if not after_game:
            return
        before_game = extract_playing_game_name(before.activities) if before else None
        if after_game == before_game:
            return
        self.logger.info(f"Presence game change for member {after.name}: {before_game} -> {after_game}", extra={
            "member": after.name,
            "before_game": before_game,
            "after_game": after_game
        })
        self.event_handler.handle_player_game_activity_event(str(after.id), after.name, after_game)

    async def on_ready(self):
        # Set trace context for bot ready event
        trace_id = logger.generate_trace_id()
        logger.set_trace_context(trace_id)
        
        self.logger.info("Pururu Discord Bot is ready!")
        self.event_handler.handle_on_ready_event()
        self._scan_voice_games()

    def _scan_voice_games(self) -> None:
        """Re-reads games of members already in voice, e.g. after a bot restart."""
        guild = self.get_guild(int(settings.discord.guild_id))
        if not guild:
            return
        for member in guild.members:
            if member.bot or member.voice is None or member.voice.channel is None:
                continue
            game = extract_playing_game_name(member.activities)
            if game:
                self.event_handler.handle_player_game_activity_event(str(member.id), member.name, game)

    def setup_commands(self):
        self.logger.debug("Setting up commands...")

        @self.tree.command(
            name='ping',
            description='Sends a ping to Pururu'
        )
        async def ping_command(interaction: discord.Interaction):
            # Set trace context for this command
            trace_id = logger.generate_trace_id()
            logger.set_trace_context(trace_id)
            
            self.logger.info("Ping command received", extra={
                "user": interaction.user.name,
                "guild": interaction.guild.name if interaction.guild else None
            })
            await interaction.response.send_message(
                f"Pong! Pururu {get_version()} is watching! :3")

        @self.tree.command(
            name="type",
            description="Change the type of the session"
        )
        async def change_type_command(interaction: discord.Interaction, session_id: str):
            # Set trace context for this command
            trace_id = logger.generate_trace_id()
            logger.set_trace_context(trace_id)
            
            self.logger.info(f"Change type command received, requester {interaction.user.name} ({interaction.user.id})",
                             extra={
                                 "player_id": interaction.user.id,
                                 "player_name": interaction.user.name,
                                 "session_id": session_id
                             })
            await interaction.response.defer(ephemeral=True)
            session = await asyncio.to_thread(self.event_handler.handle_change_type_command, session_id)
            if not session:
                await interaction.followup.send(f"Session with ID `{session_id}` not found :dumb:.")
                return
            modal = EditSessionTypeModal(session, self.event_handler.handle_session_type_change_modal_submit)
            view = discord.ui.View(timeout=60)
            button = discord.ui.Button(label="Cambiar Tipo", style=discord.ButtonStyle.primary, emoji="🔄")
            async def on_type_button_click(btn_interaction: discord.Interaction):
                await btn_interaction.response.send_modal(modal)
            button.callback = on_type_button_click
            view.add_item(button)
            await interaction.followup.send(
                f"Sesión `{session_id}` encontrada. Pulsa el botón para cambiar el tipo:", view=view)

        @self.tree.command(
            name="attendance",
            description="Edits the attendance of the session"
        )
        async def edit_attendance_command(interaction: discord.Interaction, session_id: str):
            # Set trace context for this command
            trace_id = logger.generate_trace_id()
            logger.set_trace_context(trace_id)
            
            self.logger.info(
                f"Edit attendance command received, requester {interaction.user.name} ({interaction.user.id})", extra={
                    "player_id": interaction.user.id,
                    "player_name": interaction.user.name,
                    "session_id": session_id
                })
            await interaction.response.defer(ephemeral=True)
            session = await asyncio.to_thread(self.event_handler.handle_edit_attendance_command, session_id)
            if not session:
                await interaction.followup.send(f"Session with ID `{session_id}` not found :dumb:.")
                return
            modal = EditAttendanceModal(session, self.event_handler.handle_session_attendance_edit_modal_submit)
            view = discord.ui.View(timeout=60)
            button = discord.ui.Button(label="Editar Asistencias", style=discord.ButtonStyle.primary, emoji="✏️")
            async def on_attendance_button_click(btn_interaction: discord.Interaction):
                await btn_interaction.response.send_modal(modal)
            button.callback = on_attendance_button_click
            view.add_item(button)
            await interaction.followup.send(
                f"Sesión `{session_id}` encontrada. Pulsa el botón para editar asistencias:", view=view)

        @self.tree.command(
            name="repair-attendance",
            description="Repairs missing attendance caused by incomplete Discord connection data"
        )
        async def repair_attendance_command(interaction: discord.Interaction, session_id: str):
            trace_id = logger.generate_trace_id()
            logger.set_trace_context(trace_id)
            self.logger.info(
                f"Repair attendance command received, requester {interaction.user.name} ({interaction.user.id})",
                extra={
                    "player_id": interaction.user.id,
                    "player_name": interaction.user.name,
                    "session_id": session_id
                })
            await interaction.response.defer(ephemeral=True)
            session = await asyncio.to_thread(self.event_handler.handle_repair_attendance_command, session_id)
            if not session:
                await interaction.followup.send(f"Session with ID `{session_id}` not found :dumb:.")
                return
            if not session.is_concluded():
                await interaction.followup.send("La sesión todavía no ha concluido; no se puede reparar aún.")
                return
            if not session.get_absent_players():
                await interaction.followup.send("La sesión no tiene usuarios ausentes que reparar.")
                return

            modal = RepairAttendanceModal(
                session, self.event_handler.handle_session_attendance_repair_modal_submit)
            view = discord.ui.View(timeout=60)
            button = discord.ui.Button(label="Reparar Asistencias", style=discord.ButtonStyle.primary, emoji="🩹")

            async def on_repair_button_click(btn_interaction: discord.Interaction):
                await btn_interaction.response.send_modal(modal)

            button.callback = on_repair_button_click
            view.add_item(button)
            await interaction.followup.send(
                f"Sesión `{session_id}` encontrada. Pulsa el botón y confirma quién asistió:", view=view)

    async def send_session_info_view_message(self, channel_id: str, session) -> str:
        # Set trace context for this action
        trace_id = logger.generate_trace_id()
        logger.set_trace_context(trace_id)
        
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
                                         on_session_game_edit=self.event_handler.handle_session_game_edit_modal_submit,
                                         thumbnail_url=avatar_url)
            message = await channel.send(view=view)
            return str(message.id)
        except Exception as e:
            self.logger.error(f"Failed to send session info view to channel {channel_id}",
                              extra={"session_id": session.id}, exc_info=True)
            raise DiscordUnExpectedException(f"Failed to send session info view to channel {channel_id}") from e

    async def edit_session_info_view_message(self, channel_id: str, message_id: str, session) -> None:
        # Set trace context for this action
        trace_id = logger.generate_trace_id()
        logger.set_trace_context(trace_id)
        
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
                                         on_session_game_edit=self.event_handler.handle_session_game_edit_modal_submit,
                                         thumbnail_url=avatar_url)
            await message.edit(view=view)
        except Exception:
            self.logger.error(f"Failed to edit session info view message {message_id} in channel {channel_id}",
                              extra={"session_id": session.id}, exc_info=True)
            raise DiscordUnExpectedException(
                f"Failed to edit session info view message {message_id} in channel {channel_id}")
