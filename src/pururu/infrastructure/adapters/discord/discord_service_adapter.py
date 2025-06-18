from datetime import timedelta

import discord

from pururu.common import logger
from pururu.common.exceptions import DiscordServiceException
from pururu.domain.entities import Message, Poll
from pururu.domain.services.discord_service import DiscordInterface
from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot


class DiscordServiceAdapter(DiscordInterface):
    def __init__(self, bot: PururuDiscordBot):
        self.bot = bot
        self.logger = logger.get_logger(__name__)

    async def send_message(self, message: Message) -> Message | None:
        """
        Sends a message to a Discord channel
        :param message: message, containing channel_id and content
        :raises DiscordMessageError: if the channel is not found
        :return: message containing id of the sent message
        :raises DiscordServiceException: if the channel is not found
        """
        try:
            self.logger.debug("Sending message", extra={"channel_id": message.channel_id, "content": message.content})
            channel = self.bot.get_channel(message.channel_id)
            if not channel:
                raise DiscordServiceException(f"Unable to send message, channel {message.channel_id} not found")
            sent_message: discord.Message = await channel.send(message.content)
            self.logger.debug("Message sent", extra={"channel_id": message.channel_id, "message_id": sent_message.id})
            message.message_id = sent_message.id
            return message
        except Exception as e:
            self.logger.error("Failed to send message", exc_info=True, extra={
                "channel_id": message.channel_id,
                "content": message.content,
                "message_data": message.__dict__
            })
            raise DiscordServiceException(f"Error sending message to channel {message.channel_id}") from e

    async def send_poll(self, poll: Poll) -> Poll | None:
        """
        Sends a poll to a Discord channel
        :param poll: poll, containing channel_id, question, answers, duration_hours, allow_multiple
        :raises DiscordMessageError: if the channel is not found
        :return: poll containing id of the sent poll
        :raises DiscordServiceException: if the channel is not found
        """
        try:
            self.logger.debug("Sending poll", extra={"poll_question": poll.question, "channel_id": poll.channel_id})
            channel = self.bot.get_channel(poll.channel_id)
            if not channel:
                raise DiscordServiceException(f"Unable to send poll, channel {poll.channel_id} not found")
            dc_poll: discord.Poll = discord.Poll(poll.question, timedelta(hours=poll.duration_hours),
                                                 multiple=poll.allow_multiple)
            for answer in poll.answers:
                dc_poll.add_answer(text=answer)
            sent_message: discord.Message = await channel.send(poll=dc_poll)
            self.logger.debug("Poll sent", extra={"poll_question": poll.question, "channel_id": poll.channel_id,
                                                  "message_id": sent_message.id,
                                                  "expires_at": sent_message.poll.expires_at})
            poll.expires_at = sent_message.poll.expires_at
            poll.message_id = sent_message.id
            return poll
        except Exception as e:
            self.logger.error("Failed to send poll", exc_info=True, extra={
                "poll_question": poll.question,
                "channel_id": poll.channel_id,
                "poll_data": poll.__dict__
            })
            raise DiscordServiceException(f"Error sending poll to channel: {poll.channel_id}") from e

    async def fetch_poll(self, channel_id: int, poll_id: int) -> Poll | None:
        """
        Fetches a poll from a Discord channel
        :param channel_id: the channel_id where the poll is located
        :param poll_id: the message_id of teh poll
        :raises DiscordMessageError: if the channel or poll is not found
        :return: poll containing the fetched data
        :raises DiscordServiceException: if the channel or Message is not found
        """
        try:
            self.logger.debug("Fetching poll", extra={"channel_id": channel_id, "poll_id": poll_id})
            channel = self.bot.get_channel(channel_id)
            if not channel:
                raise DiscordServiceException(f"Channel with id {channel_id} not found")
            message: discord.Message = await channel.fetch_message(poll_id)
            if not message:
                raise DiscordServiceException(f"Poll with id {poll_id} not found in channel {channel_id}")
            self.logger.debug("Poll fetched",
                              extra={"channel_id": channel_id, "poll_id": poll_id, "message_id": message.id})
            dc_poll = message.poll
            poll = Poll(dc_poll.question, channel_id, [], dc_poll.duration.total_seconds() / 3600, dc_poll.multiple)
            poll.expires_at = dc_poll.expires_at
            poll.message_id = message.id
            for answer in dc_poll.answers:
                poll.answers.append(answer.text)
                poll.results[answer.text] = answer.vote_count
            self.logger.debug("Poll parsed",
                              extra={
                                  "poll_id": message.id,
                                  "question": poll.question,
                                  "answers": poll.answers,
                                  "results": poll.results,
                                  "expires_at": str(poll.expires_at)
                              }
                              )
            return poll
        except Exception as e:
            self.logger.error("Failed to fetch poll", exc_info=True, extra={
                "channel_id": channel_id,
                "poll_id": poll_id
            })
            raise DiscordServiceException(f"Error fetching poll: {poll_id} from channel: {channel_id}") from e
