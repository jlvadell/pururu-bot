from pururu.common import logger
from pururu.config import settings
from pururu.domain.entities.session import SessionMetadataKey, Type, PlayerSession, Session
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import (PlayerJoinedSessionEvent, PlayerLeftSessionEvent,
                                                           SessionConcludeRequestedEvent, SessionConcludedEvent,
                                                           SessionTypeChangeEvent, SessionAttendanceEditEvent,
                                                           SessionUpdatedEvent, SessionCreatedEvent)
from pururu.domain.services.data_sync_service import DataSyncService
from pururu.domain.services.discord_service import DiscordService
from pururu.domain.services.session_service import SessionService


class SessionEventsHandler:
    def __init__(self, session_service: SessionService, data_sync_service: DataSyncService, event_bus: EventBus,
                 discord_service: DiscordService):
        self.session_service = session_service
        self.data_sync_service = data_sync_service
        self.event_bus = event_bus
        self.discord_service = discord_service
        self.logger = logger.get_logger(__name__)
        self._subscribe_events()

    def _subscribe_events(self) -> None:
        self.event_bus.subscribe(PlayerJoinedSessionEvent.event_type, self.handle_player_joined)
        self.event_bus.subscribe(PlayerLeftSessionEvent.event_type, self.handle_player_left)
        self.event_bus.subscribe(SessionConcludeRequestedEvent.event_type, self.handle_session_conclude_requested)
        self.event_bus.subscribe(SessionConcludedEvent.event_type, self.handle_session_concluded)
        self.event_bus.subscribe(SessionCreatedEvent.event_type, self.handle_session_created)
        self.event_bus.subscribe(SessionTypeChangeEvent.event_type, self.handle_session_type_change)
        self.event_bus.subscribe(SessionAttendanceEditEvent.event_type, self.handle_session_attendance_edit)
        self.event_bus.subscribe(SessionUpdatedEvent.event_type, self.handle_session_updated)

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

    async def handle_session_concluded(self, event: SessionConcludedEvent) -> None:
        self.logger.info(
            f"Handling SessionConcludedEvent for session {event.session_id}",
            extra={
                "session_id": event.session_id,
            })
        session = self.session_service.find_session_by_id(event.session_id)
        await self._update_session_info_view(session)
        self._sync_session(session)

    def handle_session_type_change(self, event: SessionTypeChangeEvent) -> None:
        self.logger.info(
            f"Handling SessionTypeChangeEvent for session {event.session_id} to new type {event.new_type}",
            extra={
                "session_id": event.session_id
            })
        self.session_service.change_session_type(event.session_id, Type(event.new_type))

    def handle_session_attendance_edit(self, event: SessionAttendanceEditEvent) -> None:
        self.logger.info(
            f"Handling SessionAttendanceEditEvent for session {event.session_id}",
            extra={
                "session_id": event.session_id,
            })
        players: list[PlayerSession] = []
        for player_id, justified_absence in event.justified_absences.items():
            motive = event.motives.get(player_id, "")
            players.append(PlayerSession(
                player_id=player_id,
                attended=True,  # attended is ignored
                justified_absence=justified_absence,
                motive=motive,
                intervals=[]  # intervals are ignored
            ))

        self.session_service.edit_session_attendance(event.session_id, players)

    async def handle_session_created(self, event: SessionCreatedEvent) -> None:
        self.logger.info(
            f"Handling SessionCreatedEvent for session {event.session_id}",
            extra={
                "session_id": event.session_id,
            })
        session = self.session_service.find_session_by_id(event.session_id)
        channel_id = settings.discord.discord_communication_channel_id
        message_id = await self.discord_service.send_session_info_view_message(channel_id, session)
        metadata = {SessionMetadataKey.DISCORD_INFO_MESSAGE_CHANNEL_ID: channel_id,
                    SessionMetadataKey.DISCORD_INFO_MESSAGE_ID: message_id}
        self.session_service.add_session_metadata(event.session_id, metadata)

    async def handle_session_updated(self, event: SessionUpdatedEvent) -> None:
        self.logger.info(
            f"Handling SessionUpdatedEvent for session {event.session_id}",
            extra={
                "session_id": event.session_id,
            })
        session = self.session_service.find_session_by_id(event.session_id)
        await self._update_session_info_view(session)
        self._sync_session(session)

    async def _update_session_info_view(self, session: Session) -> None:
        channel_id = session.metadata.get(SessionMetadataKey.DISCORD_INFO_MESSAGE_CHANNEL_ID)
        message_id = session.metadata.get(SessionMetadataKey.DISCORD_INFO_MESSAGE_ID)
        await self.discord_service.update_session_info_view_message(channel_id, message_id, session)

    def _sync_session(self, session: Session) -> None:
        if session.was_concluded_positively():
            self.data_sync_service.sync_session(session)
