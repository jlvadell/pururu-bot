from abc import ABC, abstractmethod

from pururu.domain.entities import BotEvent

class EventService(ABC):
    @abstractmethod
    def publish(self, event: BotEvent) -> None:
        pass