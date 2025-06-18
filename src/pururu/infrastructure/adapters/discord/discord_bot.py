import discord
from discord.ext import commands

import pururu.config as config
from pururu.application.services.pururu_handler import PururuHandler
from pururu.common import logger


class PururuDiscordBot(commands.Bot):
    def __init__(self, pururu_handler: PururuHandler):
        intents = discord.Intents.default()
        super().__init__(command_prefix="/", intents=intents)
        self.logger = logger.get_logger(__name__)
        self.pururu_handler = pururu_handler

    async def setup_hook(self) -> None:
        self.setup_commands()
        guild = discord.Object(id=config.GUILD_ID)
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        result = await self.tree.sync(guild=guild)
        self.logger.info("Commands synced successfully", extra={
            "guild_id": config.GUILD_ID,
            "command_count": len(result),
            "commands": [x.name for x in result]
        })

    async def on_voice_state_update(self, member: discord.Member, before_state: discord.VoiceState,
                                    after_state: discord.VoiceState):
        self.logger.info("Voice state changed", extra={
            "member": member.name,
            "before_channel": before_state.channel.name if before_state.channel else None,
            "after_channel": after_state.channel.name if after_state.channel else None
        })
        self.pururu_handler.handle_voice_state_update_dc_event(member.name,
                                                               before_state.channel.name if before_state.channel else None,
                                                               after_state.channel.name if after_state.channel else None)

    async def on_ready(self):
        self.logger.info("Pururu Discord Bot is ready!")
        self.pururu_handler.handle_on_ready_dc_event()

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
                f"Pong! Pururu v{config.APP_VERSION} is watching! :3")

        @self.tree.command(
            name='stats',
            description='Shows your attendance stats')
        async def stats_command(interaction: discord.Interaction):
            self.logger.info("Stats command received", extra={
                "user": interaction.user.name,
                "guild": interaction.guild.name if interaction.guild else None
            })
            await interaction.response.defer(ephemeral=True, thinking=True)
            try:
                member_stats = self.pururu_handler.retrieve_player_stats(interaction.user.name)
                await interaction.followup.send(f"Hola {interaction.user.mention}! Estos son tus Stats:\n" +
                                                member_stats.as_message())
            except Exception:
                self.logger.error("Failed to retrieve stats", exc_info=True, extra={
                    "user": interaction.user.name,
                    "guild": interaction.guild.name if interaction.guild else None
                })
                await interaction.followup.send("Ooops! Something went wrong with that :(")
