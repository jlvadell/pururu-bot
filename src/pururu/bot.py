import discord
from discord import app_commands

import pururu.config as config
import pururu.utils as utils
from pururu.application.events.event_system import EventSystem
from pururu.application.events.listeners import EventListeners
from pururu.domain.services.pururu_service import PururuService
from pururu.infrastructure.adapters.google_sheets.google_sheets_adapter import GoogleSheetsAdapter
from pururu.__version__ import __version__


class Application:
    def __init__(self):
        self.db_service = None
        self.event_system = None
        self.pururu_service = None
        self.event_listeners = None
        self.dc_command_tree = None
        self.dc_client = None
        self.logger = utils.get_logger(__name__)

    def setup_discord_events(self):
        @self.dc_client.event
        async def on_voice_state_update(member, before_state, after_state):
            self.logger.debug(f'{member.name} has changed voice state from {before_state} to {after_state}')
            self.pururu_service.handle_voice_state_update(member.name, before_state.channel, after_state.channel)

        @self.dc_command_tree.command(
            name='ping',
            description='Sends a ping to Pururu',
            guild = discord.Object(id=config.GUILD_ID)
        )
        async def ping_command(interaction: discord.Interaction):
            await interaction.response.send_message(f"Pong! Pururu v{__version__} is watching! :3")

        @self.dc_command_tree.command(
            name='stats',
            description='Shows your attendance stats',
            guild = discord.Object(id=config.GUILD_ID)
        )
        async def stats_command(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral = True, thinking = True)
            member_stats = self.pururu_service.retrieve_player_stats(interaction.user.name)
            await interaction.followup.send(f"Hola {interaction.user.mention}! Estos son tus Stats:\n" +
                                                    member_stats.as_message())
        @self.dc_client.event
        async def on_ready():
            self.logger.info(f'Application Started and connected to {",".join([guild.name for guild in self.dc_client.guilds])}')
            guild = filter(lambda x: x.id == config.GUILD_ID, self.dc_client.guilds)
            if guild:
                guild = list(guild)[0]
                self.dc_command_tree.clear_commands(guild=guild)
                self.dc_command_tree.copy_global_to(guild=guild)
                result = await self.dc_command_tree.sync(guild=guild)
                self.logger.debug(f"Commands synced: {result}")

    def init(self):
        # ----------------------------------------
        # -------------- Setup Adapters
        # ----------------------------------------
        self.db_service = GoogleSheetsAdapter(config.GOOGLE_SHEETS_CREDENTIALS, config.SPREADSHEET_ID)

        # ----------------------------------------
        # -------------- Setup Application services
        # ----------------------------------------
        self.event_system = EventSystem()
        self.pururu_service = PururuService(self.db_service, self.event_system)
        self.event_listeners = EventListeners(self.event_system, self.pururu_service)

        # ----------------------------------------
        # -------------- Setup Discord client
        # ----------------------------------------
        intents = discord.Intents.default()
        self.dc_client = discord.Client(intents=intents)
        self.dc_command_tree = app_commands.CommandTree(self.dc_client)
        self.setup_discord_events()

        # ----------------------------------------
        # -------------- RUN APP
        # ----------------------------------------
        self.dc_client.run(config.DISCORD_TOKEN)


if __name__ == '__main__':
    app = Application()
    app.init()
