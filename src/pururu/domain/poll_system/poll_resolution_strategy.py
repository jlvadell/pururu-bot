from abc import ABC, abstractmethod

from pururu.domain.entities import Poll, Message


class PollResolutionStrategy(ABC):
    @abstractmethod
    async def resolve(self, poll: Poll) -> Message | None:
        pass


class SendMessagePollResolution(PollResolutionStrategy):
    def __init__(self, discord_service):
        self.discord_service = discord_service

    async def resolve(self, poll: Poll) -> Message | None:
        message = Message(f"{poll.question}\nOpción/es ganadoras: {poll.get_winners()}", poll.channel_id)
        sent_message = await self.discord_service.send_message(message)
        return sent_message
