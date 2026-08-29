from pururu.common import logger
from pururu.config import settings
from pururu.domain.entities.session import SessionMetadataKey, Type, PlayerSession, Session
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import (PlayerJoinedSessionEvent, PlayerLeftSessionEvent,
                                                           SessionConcludeRequestedEvent, SessionConcludedEvent,
                                                           SessionTypeChangeEvent, SessionAttendanceEditEvent,
                                                           SessionAttendanceRepairEvent, SessionUpdatedEvent,
                                                           SessionCreatedEvent, PlayerGameDetectedEvent,
                                                           SessionGameEditEvent)
from pururu.domain.services.data_sync_service import DataSyncService
from pururu.domain.services.discord_service import DiscordService
from pururu.domain.services.session_service import SessionService
from pururu.infrastructure.adapters.keronworld.session_packs_client import post_session_packs

_DEFAULT_KERONWORLD_APP_URL = "https://app.keronworld.org"


def _as_bool(value) -> bool:
    if value is True or value == 1:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _as_str(value) -> str:
    return value.strip() if isinstance(value, str) else ""


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
        self.event_bus.subscribe(SessionAttendanceRepairEvent.event_type, self.handle_session_attendance_repair)
        self.event_bus.subscribe(SessionUpdatedEvent.event_type, self.handle_session_updated)
        self.event_bus.subscribe(PlayerGameDetectedEvent.event_type, self.handle_player_game_detected)
        self.event_bus.subscribe(SessionGameEditEvent.event_type, self.handle_session_game_edit)

    async def handle_player_joined(self, event: PlayerJoinedSessionEvent) -> None:
        self.logger.info(
            f"Handling PlayerJoinedSessionEvent for player {event.player_id} at time {event.time.isoformat()}", extra={
                "player_id": event.player_id,
                "time": event.time.isoformat()
            })
        session = self.session_service.register_player_connection(event.player_id, event.time)
        game_name = await self.discord_service.get_playing_game(event.player_id)
        if game_name:
            self.session_service.record_player_game(event.player_id, game_name)
            session = self.session_service.find_session_by_id(session.id)
        await self._update_session_info_view(session)

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
        await self._notify_session_packs(session)

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

    def handle_session_attendance_repair(self, event: SessionAttendanceRepairEvent) -> None:
        self.logger.info(
            f"Handling SessionAttendanceRepairEvent for session {event.session_id}",
            extra={"session_id": event.session_id, "player_ids": event.player_ids})
        self.session_service.repair_session_attendance(event.session_id, event.player_ids)

    def handle_player_game_detected(self, event: PlayerGameDetectedEvent) -> None:
        self.logger.info(
            f"Handling PlayerGameDetectedEvent for player {event.player_id} playing {event.game_name}",
            extra={"player_id": event.player_id, "game_name": event.game_name})
        self.session_service.record_player_game(event.player_id, event.game_name)

    def handle_session_game_edit(self, event: SessionGameEditEvent) -> None:
        self.logger.info(
            f"Handling SessionGameEditEvent for session {event.session_id} to game {event.game_name}",
            extra={"session_id": event.session_id, "game_name": event.game_name})
        self.session_service.set_session_game(event.session_id, event.game_name)

    async def handle_session_created(self, event: SessionCreatedEvent) -> None:
        self.logger.info(
            f"Handling SessionCreatedEvent for session {event.session_id}",
            extra={
                "session_id": event.session_id,
            })
        if settings.discord.enable_communication_channel:
            session = self.session_service.find_session_by_id(event.session_id)
            channel_id = settings.discord.discord_communication_channel_id
            message_id = await self.discord_service.send_session_info_view_message(channel_id, session)
            if not message_id:
                self.logger.error(f"Failed to send session info view message for session {event.session_id}",
                                  extra={"session_id": event.session_id})
                return
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
        if settings.discord.enable_communication_channel:
            channel_id = session.metadata.get(SessionMetadataKey.DISCORD_INFO_MESSAGE_CHANNEL_ID)
            message_id = session.metadata.get(SessionMetadataKey.DISCORD_INFO_MESSAGE_ID)
            if channel_id and message_id:
                await self.discord_service.update_session_info_view_message(channel_id, message_id, session)

    def _sync_session(self, session: Session) -> None:
        if session.was_concluded_positively():
            self.data_sync_service.sync_session(session)

    async def _notify_session_packs(self, session: Session) -> None:
        if not session.was_concluded_positively():
            return
        enabled, packs_url, packs_secret, app_url = self._keronworld_packs_config()
        if not enabled or not packs_url or not packs_secret:
            return
        attendees = [ps for ps in (session.players or []) if getattr(ps, "attended", False) is True]
        if not attendees:
            self.logger.info(
                "Skipping KeroWorld pack notify; no attendees",
                extra={"session_id": session.id},
            )
            return
        payload = self._build_session_packs_payload(session, attendees)
        try:
            result = await post_session_packs(packs_url, packs_secret, payload)
        except Exception:
            self.logger.error(
                "KeroWorld pack notify raised unexpectedly",
                extra={"session_id": session.id},
                exc_info=True,
            )
            return
        if result is None or not (200 <= result.status_code < 300):
            return
        if result.body.get("missingChestType") is True or result.body.get("success") is False:
            self.logger.warning(
                "KeroWorld pack notify did not grant packs; skipping Discord message",
                extra={
                    "session_id": session.id,
                    "success": result.body.get("success"),
                    "missing_chest_type": result.body.get("missingChestType"),
                },
            )
            return
        await self._send_session_packs_discord_message(session, attendees, result.body, app_url)

    def _keronworld_packs_config(self) -> tuple[bool, str, str, str]:
        try:
            keronworld = getattr(settings, "keronworld", None)
        except Exception:
            keronworld = None
        if keronworld is None:
            return False, "", "", _DEFAULT_KERONWORLD_APP_URL
        enabled = _as_bool(getattr(keronworld, "enabled", False))
        packs_url = _as_str(getattr(keronworld, "packs_url", ""))
        packs_secret = _as_str(getattr(keronworld, "packs_secret", ""))
        app_url = _as_str(getattr(keronworld, "app_url", "")) or _DEFAULT_KERONWORLD_APP_URL
        return enabled, packs_url, packs_secret, app_url

    def _build_session_packs_payload(self, session: Session, attendees: list[PlayerSession]) -> dict:
        payload: dict = {
            "sessionId": session.id,
            "attendees": [{"discordId": ps.player_id} for ps in attendees],
        }
        session_type = getattr(session, "type", None)
        if session_type is not None:
            value = getattr(session_type, "value", None)
            payload["sessionType"] = value if isinstance(value, str) else str(session_type)
        game_name = None
        getter = getattr(session, "get_game_name", None)
        if callable(getter):
            try:
                game_name = getter()
            except Exception:
                game_name = None
        if isinstance(game_name, str) and game_name.strip():
            payload["gameName"] = game_name.strip()
        return payload

    async def _send_session_packs_discord_message(
            self, session: Session, attendees: list[PlayerSession], body: dict, app_url: str) -> None:
        channel_id = getattr(settings.discord, "discord_communication_channel_id", None)
        if not channel_id:
            self.logger.warning(
                "Skipping Discord pack message; discord_communication_channel_id is not set",
                extra={"session_id": session.id},
            )
            return
        granted = [str(item) for item in (body.get("granted") or []) if item]
        skipped = [str(item) for item in (body.get("skipped") or []) if item]
        if granted:
            mentions = " ".join(f"<@{discord_id}>" for discord_id in granted)
            content = f"Hay un sobre de cartas para {mentions}. Ábrelo en {app_url}"
        elif skipped:
            content = f"Ya teníais sobre de esta sesión. {app_url}"
        else:
            mentions = " ".join(f"<@{ps.player_id}>" for ps in attendees)
            content = f"Hay un sobre de cartas para {mentions}. Ábrelo en {app_url}"
        try:
            await self.discord_service.send_simple_message(str(channel_id), content)
        except Exception:
            self.logger.error(
                "Failed to send Discord pack message",
                extra={"session_id": session.id, "channel_id": str(channel_id)},
                exc_info=True,
            )

