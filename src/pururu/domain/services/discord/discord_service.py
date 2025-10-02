from abc import ABC, abstractmethod

from pururu.domain.entities.poll import PollReference, Poll
from pururu.domain.services.discord.discord_entities import SimpleMessage


class DiscordService(ABC):
    @abstractmethod
    async def fetch_poll(self, poll: PollReference) -> Poll | None:
        pass

    @abstractmethod
    async def send_simple_message(self, message: SimpleMessage) -> SimpleMessage | None:
        pass
