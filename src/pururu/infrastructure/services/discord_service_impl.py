import discord

from pururu.common import logger
from pururu.domain.entities.poll import PollReference, Poll
from pururu.domain.services.discord.discord_entities import SimpleMessage
from pururu.domain.services.discord.discord_service import DiscordService
from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot


class DiscordServiceImpl(DiscordService):
    def __init__(self, bot: PururuDiscordBot):
        self.bot = bot
        self.logger = logger.get_logger(__name__)

    async def send_simple_message(self, message: SimpleMessage) -> SimpleMessage | None:
        """
        Sends a message to a Discord channel
        :param message: message, containing channel_id and content
        :return: message containing id of the sent message or None if failed
        """
        channel = self.bot.get_channel(int(message.channel_id))
        if not channel:
            self.logger.error(f"Failed to send message to channel {message.channel_id}", extra={
                "channel_id": message.channel_id
            })
            return None
        sent_message: discord.Message = await channel.send(message.content)
        self.logger.debug(f"Message sent to channel {message.channel_id} with id {sent_message.id}",
                          extra={"channel_id": message.channel_id, "message_id": sent_message.id})
        message.id = sent_message.id
        return message

    async def fetch_poll(self, poll: PollReference) -> Poll | None:
        """
        Fetches a poll from a Discord channel
        :param poll: poll reference, containing channel_id and poll_id
        :return: poll containing the fetched data or None if not found
        """
        self.logger.debug(f"Fetching poll with id '{poll.id}' in channel {poll.channel_id}",
                          extra={"channel_id": poll.channel_id, "message_id": poll.id})
        channel = self.bot.get_channel(int(poll.channel_id))
        if not channel:
            self.logger.error(f"Unable to fetch poll, channel {poll.channel_id} not found")
            return None
        message: discord.Message = await channel.fetch_message(int(poll.id))
        if not message:
            self.logger.error(f"Unable to fetch poll, message {poll.id} not found")
            return None
        self.logger.debug(f"Poll {poll.id} fetched",
                          extra={"channel_id": poll.channel_id, "message_id": message.id})
        dc_poll = message.poll
        result = Poll(dc_poll.id, poll.channel_id, dc_poll.expires_at, poll.resolution_type, dc_poll.question, [],
                      dc_poll.duration.total_seconds() / 3600, dc_poll.multiple)
        for answer in dc_poll.answers:
            result.answers.append(answer.text)
            result.results[answer.text] = answer.vote_count
        return result
