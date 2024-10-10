from abc import ABC, abstractmethod

from pururu.domain.entities import Message, Poll


class DiscordInterface(ABC):
    @abstractmethod
    async def send_message(self, message: Message) -> Message | None:
        pass

    @abstractmethod
    async def send_poll(self, poll: Poll) -> Poll | None:
        pass

    @abstractmethod
    async def fetch_poll(self, channel_id: int, poll_id: int) -> Poll | None:
        pass
