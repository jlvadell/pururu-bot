from datetime import timedelta

import discord

import pururu.config as config
import pururu.utils as utils
from pururu.domain.entities import Message, Poll
from pururu.domain.exceptions import DiscordServiceException
from pururu.domain.services.discord_service import DiscordInterface
from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot


class DiscordServiceAdapter(DiscordInterface):
    def __init__(self, bot: PururuDiscordBot):
        self.bot = bot
        self.guild: discord.Guild = next(filter(lambda guild: guild.id == config.GUILD_ID, self.bot.guilds), None)
        self.logger = utils.get_logger(__name__)

    async def send_message(self, message: Message) -> Message | None:
        """
        Sends a message to a Discord channel
        :param message: message, containing channel_id and content
        :raises DiscordMessageError: if the channel is not found
        :return: message containing id of the sent message
        :raises DiscordServiceException: if the channel is not found
        """
        self.logger.debug(f"Sending message: {message.content}")
        channel = self.guild.get_channel(message.channel_id)
        if not channel:
            raise DiscordServiceException(f"Unable to send message, channel {message.channel_id} not found")
        sent_message: discord.Message = await channel.send(message.content)
        self.logger.debug(f"Message sent: {sent_message.content}, with id {sent_message.id}")
        message.message_id = sent_message.id
        return message

    async def send_poll(self, poll: Poll) -> Poll | None:
        """
        Sends a poll to a Discord channel
        :param poll: poll, containing channel_id, question, answers, duration_hours, allow_multiple
        :raises DiscordMessageError: if the channel is not found
        :return: poll containing id of the sent poll
        :raises DiscordServiceException: if the channel is not found
        """
        self.logger.debug(f"Sending poll: {poll.question}")
        channel = self.guild.get_channel(poll.channel_id)
        if not channel:
            raise DiscordServiceException(f"Unable to send poll, channel {poll.channel_id} not found")
        dc_poll: discord.Poll = discord.Poll(poll.question, timedelta(hours=poll.duration_hours),
                                             multiple=poll.allow_multiple)
        for answer in poll.answers:
            dc_poll.add_answer(text=answer)
        sent_message: discord.Message = await channel.send(poll=dc_poll)
        self.logger.debug(f"Poll sent: {sent_message.content}")
        poll.expires_at = sent_message.poll.expires_at
        poll.message_id = sent_message.id
        return poll

    async def fetch_poll(self, channel_id: int, poll_id: int) -> Poll | None:
        """
        Fetches a poll from a Discord channel
        :param channel_id: the channel_id where the poll is located
        :param poll_id: the message_id of teh poll
        :raises DiscordMessageError: if the channel or poll is not found
        :return: poll containing the fetched data
        :raises DiscordServiceException: if the channel or Message is not found
        """
        self.logger.debug(f"Fetching poll: {poll_id} from channel {channel_id}")
        channel = self.guild.get_channel(channel_id)
        if not channel:
            raise DiscordServiceException(f"Channel with id {channel_id} not found")
        message: discord.Message = await channel.fetch_message(poll_id)
        if not message:
            raise DiscordServiceException(f"Poll with id {poll_id} not found in channel {channel_id}")
        self.logger.debug(f"Poll {message.id} fetched")
        dc_poll = message.poll
        poll = Poll(dc_poll.question, channel_id, [], dc_poll.duration.hours, dc_poll.multiple)
        poll.expires_at = dc_poll.expires_at
        poll.message_id = message.id
        for answer in dc_poll.answers:
            poll.answers.append(answer.text)
            poll.results[answer.text] = answer.count
        return poll
