import discord
from pururu.domain.entities import Message
from pururu.domain.services.discord_service import DiscordInterface
import pururu.config as config
import pururu.utils as utils

class DiscordServiceAdapter(DiscordInterface):
    def __init__(self):
        intents = discord.Intents.default()
        self.client: discord.Client = discord.Client(intents=intents)
        self.guild: discord.Guild = next(filter(lambda guild: guild.id == config.GUILD_ID, self.client.guilds), None)
        self.logger = utils.get_logger(__name__)

    def get_client(self) -> discord.Client:
        return self.client

    async def send_message(self, message: Message) -> Message:
        for channel in self.guild.text_channels:
            if channel.id == message.channel_id:
                sent_message: discord.Message = await channel.send(message.content)
                self.logger.debug(f"Message sent: {sent_message.content}")
                message.message_id = sent_message.id
            else:
                self.logger.error(f"Channel {message.channel_id} not found for message: {message.content}")
        return message



