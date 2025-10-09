import discord
from discord.ext import commands

from pururu.__version__ import get_version
from pururu.application.handlers.discord_event_handler import DiscordEventHandler
from pururu.common import logger
from pururu.config import settings


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
