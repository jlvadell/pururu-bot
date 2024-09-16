import discord
import pururu.utils as utils
import pururu.config as config
import pururu.domain.services.pururu_service


class DiscordEventHandler:
    def __init__(self, dc_client: discord.Client, pururu_service: pururu.domain.services.pururu_service.PururuService):
        self.dc_client = dc_client
        self.pururu_service = pururu_service
        self.dc_command_tree = discord.app_commands.CommandTree(self.dc_client)
        self.logger = utils.get_logger(__name__)
        # ------------------------------
        # Setup Discord Events
        # ------------------------------
        self.dc_client.event(self.on_ready)
        self.dc_client.event(self.on_voice_state_update)
        # ------------------------------
        # Setup Discord Slash Commands
        # ------------------------------
        self.dc_command_tree.add_command(self.ping_command)
        self.dc_command_tree.add_command(self.stats_command)

    # ------------------------------
    # EVENT HANDLER
    # ------------------------------
    async def on_ready(self):
        self.logger.info(
            f'Application Started and connected to {",".join([guild.name for guild in self.dc_client.guilds])}')
        guild = list(filter(lambda x: x.id == config.GUILD_ID, self.dc_client.guilds))
        if guild:
            guild = guild[0]
            self.dc_command_tree.clear_commands(guild=guild)
            self.dc_command_tree.copy_global_to(guild=guild)
            result = await self.dc_command_tree.sync(guild=guild)
            self.logger.debug(f"Commands synced: {result}")

    async def on_voice_state_update(self, member: discord.Member, before_state: discord.VoiceState,
                                    after_state: discord.VoiceState):
        self.logger.debug(f'{member.name} has changed voice state from {before_state} to {after_state}')
        self.pururu_service.handle_voice_state_update(member.name,
                                                      before_state.channel.name if before_state.channel else None,
                                                      after_state.channel.name if after_state.channel else None)

    # ------------------------------
    # SLASH COMMAND HANDLER
    # ------------------------------

    @discord.app_commands.command(
        name='ping',
        description='Sends a ping to Pururu',
    )
    async def ping_command(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Pong! Pururu v{config.APP_VERSION} is watching! :3{'\n' + config.PING_MESSAGE 
            if config.PING_MESSAGE else ''}")

    @discord.app_commands.command(
        name='stats',
        description='Shows your attendance stats',
    )
    async def stats_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        member_stats = self.pururu_service.retrieve_player_stats(interaction.user.name)
        await interaction.followup.send(f"Hola {interaction.user.mention}! Estos son tus Stats:\n" +
                                        member_stats.as_message())
