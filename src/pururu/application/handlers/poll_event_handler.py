from datetime import datetime

from pururu.common import logger
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.secondary_events import (CheckExpiredPollsEvent, FinalizePollEvent)
from pururu.domain.services.poll_system.poll_system_service import PollSystemService


class PollEventHandler:
    def __init__(self, event_bus: EventBus, poll_system_service: PollSystemService):
        self.event_bus = event_bus
        self.poll_system_service = poll_system_service
        self.logger = logger.get_logger(__name__)
        self._subscribe_events()

    def _subscribe_events(self) -> None:
        self.event_bus.subscribe(CheckExpiredPollsEvent.event_type, self.handle_check_expired_polls_event)
        self.event_bus.subscribe(FinalizePollEvent.event_type, self.handle_finalize_poll_event)

    def handle_check_expired_polls_event(self, event: CheckExpiredPollsEvent) -> None:
        """
        Handles the CheckExpiredPollsEvent
        :param event: PururuEvent
        :return: None
        """
        expired_polls = self.poll_system_service.get_expired_polls()
        for poll in expired_polls:
            self.event_bus.publish(FinalizePollEvent(datetime.now(), poll.id))
        self.logger.info(f"Consumed CheckExpiredPollsEvent, total polls {len(expired_polls)}",
                         extra={"expired_count": len(expired_polls)})

    async def handle_finalize_poll_event(self, event: FinalizePollEvent) -> None:
        """
        Handles the FinalizePollEvent
        :param event: PururuEvent
        :return: None
        """
        await self.poll_system_service.finalize_poll(event.poll_id)
        self.logger.debug(f"Poll with id {event.poll_id} finalized", extra={
            "poll_id": event.poll_id
        })
