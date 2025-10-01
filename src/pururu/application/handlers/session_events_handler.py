from pururu.common import logger
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import (PlayerJoinedSessionEvent, PlayerLeftSessionEvent,
                                                           SessionConcludeRequestedEvent, SessionConcludedEvent)
from pururu.domain.services.data_sync_service import DataSyncService
from pururu.domain.services.session_service import SessionService


class SessionEventsHandler:
    def __init__(self, session_service: SessionService, data_sync_service: DataSyncService, event_bus: EventBus):
        self.session_service = session_service
        self.data_sync_service = data_sync_service
        self.event_bus = event_bus
        self.logger = logger.get_logger(__name__)
        self._subscribe_events()

    def _subscribe_events(self) -> None:
        self.event_bus.subscribe(PlayerJoinedSessionEvent.event_type, self.handle_player_joined)
        self.event_bus.subscribe(PlayerLeftSessionEvent.event_type, self.handle_player_left)
        self.event_bus.subscribe(SessionConcludeRequestedEvent.event_type, self.handle_session_conclude_requested)
        self.event_bus.subscribe(SessionConcludedEvent.event_type, self.handle_session_concluded)

    def handle_player_joined(self, event: PlayerJoinedSessionEvent) -> None:
        self.logger.info(
            f"Handling PlayerJoinedSessionEvent for player {event.player_id} at time {event.time.isoformat()}", extra={
                "player_id": event.player_id,
                "time": event.time.isoformat()
            })
        self.session_service.register_player_connection(event.player_id, event.time)

    def handle_player_left(self, event: PlayerLeftSessionEvent) -> None:
        self.logger.info(
            f"Handling PlayerLeftSessionEvent for player {event.player_id} at time {event.time.isoformat()}", extra={
                "player_id": event.player_id,
                "time": event.time.isoformat()
            })
        self.session_service.register_player_disconnection(event.player_id, event.time)

    def handle_session_conclude_requested(self, event: SessionConcludeRequestedEvent) -> None:
        self.logger.info(
            f"Handling SessionConcludeRequested for session {event.session_id} at time {event.end_time.isoformat()}",
            extra={
                "session_id": event.session_id,
                "time": event.end_time.isoformat()
            })
        self.session_service.conclude_session(event.session_id, event.end_time)

    def handle_session_concluded(self, event: SessionConcludedEvent) -> None:
        self.logger.info(
            f"Handling SessionConcludedEvent for session {event.session_id}",
            extra={
                "session_id": event.session_id,
            })
        session = self.session_service.find_session_by_id(event.session_id)
        if not session.was_concluded_positively():
            self.logger.info(
                f"Session {event.session_id} was not concluded positively, skipping data sync",
                extra={
                    "session_id": event.session_id,
                })
            return
        self.data_sync_service.sync_session(session)
