from abc import ABC, abstractmethod

from pururu.domain.entities import BotEvent

class EventService(ABC):
    @abstractmethod
    def publish(self, event: BotEvent) -> None:
        pass

    @abstractmethod
    async def publish_with_delay(self, event: BotEvent, delay_seconds: int) -> None:
        pass