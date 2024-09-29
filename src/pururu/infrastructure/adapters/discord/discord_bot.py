import discord
from discord.ext import commands

import pururu.config as config
import pururu.utils as utils
from pururu.application.services.pururu_handler import PururuHandler


class PururuDiscordBot(commands.Bot):
    def __init__(self, pururu_handler: PururuHandler):
        intents = discord.Intents.default()
        super().__init__(command_prefix="/", intents=intents)
        self.logger = utils.get_logger(__name__)
        self.pururu_handler = pururu_handler

    async def setup_hook(self) -> None:
        self.setup_commands()
        guild = discord.Object(id=config.GUILD_ID)
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        result = await self.tree.sync(guild=guild)
        self.logger.debug(f"Commands synced: {",".join([x.name for x in result])}")

    async def on_voice_state_update(self, member: discord.Member, before_state: discord.VoiceState,
                                    after_state: discord.VoiceState):
        self.logger.debug(f'{member.name} has changed voice state from {before_state} to {after_state}')
        self.pururu_handler.handle_voice_state_update_dc_event(member.name,
                                                               before_state.channel.name if before_state.channel else None,
                                                               after_state.channel.name if after_state.channel else None)

    async def on_ready(self):
        self.logger.info(
            f'Application Started and connected to {",".join([guild.name for guild in self.guilds])}')

    def setup_commands(self):
        @self.tree.command(
            name='ping',
            description='Sends a ping to Pururu'
        )
        async def ping_command(interaction: discord.Interaction):
            await interaction.response.send_message(
                f"Pong! Pururu v{config.APP_VERSION} is watching! :3{'\n' + config.PING_MESSAGE if config.PING_MESSAGE else ''}")

        @self.tree.command(
            name='stats',
            description='Shows your attendance stats')
        async def stats_command(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True, thinking=True)
            member_stats = self.pururu_handler.retrieve_player_stats(interaction.user.name)
            await interaction.followup.send(f"Hola {interaction.user.mention}! Estos son tus Stats:\n" +
                                            member_stats.as_message())
