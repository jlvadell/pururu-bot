from collections.abc import Callable

from typing_extensions import Protocol

from pururu.domain.messaging.events.base_events import DomainEvent


class EventBus(Protocol):
    def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to the event bus.
        :param event: The event to be published.
        :return: None
        """
        pass

    def subscribe(self, event_type: str, handler: Callable[['DomainEvent'], None]) -> None:
        """
        Subscribe a handler to a specific event type.
        :param event_type: The type of event to subscribe to.
        :param handler: The handler function to be called when the event is published.
        :return: None
        """
        pass
