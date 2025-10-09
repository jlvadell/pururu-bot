import discord

from pururu.common import logger
from pururu.domain.entities.poll import PollReference, Poll
from pururu.domain.services.discord_service import DiscordService
from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot


class DiscordServiceImpl(DiscordService):
    def __init__(self, bot: PururuDiscordBot):
        self.bot = bot
        self.logger = logger.get_logger(__name__)

    async def send_simple_message(self, channel_id: str, content: str) -> bool:
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            self.logger.error(f"Failed to send message to channel {channel_id}", extra={
                "channel_id": channel_id
            })
            return False
        sent_message: discord.Message = await channel.send(content)
        self.logger.debug(f"Message sent to channel {channel_id} with id {sent_message.id}",
                          extra={"channel_id": channel_id, "message_id": sent_message.id})
        return True

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

    async def send_session_info_view_message(self, channel_id: str, session) -> str:
        self.logger.debug(f"Sending session info view message to channel {channel_id} for session {session.id}")
        return await self.bot.send_session_info_view_message(channel_id, session)

    async def update_session_info_view_message(self, channel_id: str, message_id: str, session) -> None:
        await self.bot.edit_session_info_view_message(channel_id, message_id, session)
