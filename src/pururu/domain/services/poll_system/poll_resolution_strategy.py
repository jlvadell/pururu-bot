from abc import ABC, abstractmethod

from pururu.common import logger
from pururu.domain.entities.poll import Poll
from pururu.domain.services.discord_service import DiscordService


class PollResolutionStrategy(ABC):

    def __init__(self, name: str):
        self.logger = logger.get_logger(name)

    @abstractmethod
    async def resolve(self, poll: Poll) -> None:
        pass


class SendMessagePollResolution(PollResolutionStrategy):
    def __init__(self, discord_service: DiscordService):
        super().__init__(__name__)
        self.discord_service = discord_service

    async def resolve(self, poll: Poll) -> None:
        self.logger.debug(f"Resolving poll with id '{poll.id}' in channel '{poll.channel_id}'",
                          extra={"message_id": poll.id, "channel_id": poll.channel_id})
        await self.discord_service.send_simple_message(poll.channel_id,
                                                       f"{poll.question}\nResults: {poll.get_winners()}")
