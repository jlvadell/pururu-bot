import discord

import pururu.config as config
import pururu.utils as utils
from pururu.domain.entities import Message
from pururu.domain.services.discord_service import DiscordInterface
from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot


class DiscordServiceAdapter(DiscordInterface):
    def __init__(self, bot: PururuDiscordBot):
        self.bot = bot
        self.guild: discord.Guild = next(filter(lambda guild: guild.id == config.GUILD_ID, self.bot.guilds), None)
        self.logger = utils.get_logger(__name__)

    async def send_message(self, message: Message) -> Message:
        for channel in self.guild.text_channels:
            if channel.id == message.channel_id:
                sent_message: discord.Message = await channel.send(message.content)
                self.logger.debug(f"Message sent: {sent_message.content}")
                message.message_id = sent_message.id
            else:
                self.logger.error(f"Channel {message.channel_id} not found for message: {message.content}")
        return message
