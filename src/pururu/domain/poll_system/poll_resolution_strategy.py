from abc import ABC, abstractmethod

from pururu.common import logger
from pururu.domain.entities import Poll, Message


class PollResolutionStrategy(ABC):

    def __init__(self, name: str):
        self.logger = logger.get_logger(name)

    @abstractmethod
    async def resolve(self, poll: Poll) -> Message | None:
        pass


class SendMessagePollResolution(PollResolutionStrategy):
    def __init__(self, discord_service):
        super().__init__(__name__)
        self.discord_service = discord_service

    async def resolve(self, poll: Poll) -> Message | None:
        self.logger.debug(f"Resolving poll with id '{poll.message_id}' in channel '{poll.channel_id}'",
                          extra={"poll_id": poll.message_id, "channel_id": poll.channel_id, "question": poll.question,
                                 "winners": poll.get_winners()})
        try:
            message = Message(f"{poll.question}\nOpción/es ganadoras: {poll.get_winners()}", poll.channel_id)
            sent_message = await self.discord_service.send_message(message)
            return sent_message
        except Exception:
            self.logger.error(f"Failed to resolve poll with id {poll.message_id}", exc_info=True, extra={
                "poll_id": poll.message_id,
                "channel_id": poll.channel_id,
                "question": poll.question,
                "winners": poll.get_winners()
            })
            raise
