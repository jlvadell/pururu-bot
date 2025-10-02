from collections.abc import Callable

from typing_extensions import Protocol
from pururu.domain.messaging.events.base_events import DomainEvent


class EventBus(Protocol):
    def publish(self, event: DomainEvent) -> None:
        pass
    def subscribe(self, event_type: str, handler: Callable[['DomainEvent'], None]) -> None:
        pass