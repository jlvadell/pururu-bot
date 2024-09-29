from abc import ABC, abstractmethod

from pururu.domain.entities import Message


class DiscordInterface(ABC):
    @abstractmethod
    async def send_message(self, message: Message) -> Message:
        pass