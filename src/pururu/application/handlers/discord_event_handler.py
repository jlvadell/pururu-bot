from datetime import datetime

from pururu.common import logger
from pururu.config import settings
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import (PlayerJoinedSessionEvent, PlayerLeftSessionEvent,
                                                           SessionTypeChangeEvent, SessionAttendanceEditEvent)


class DiscordEventHandler:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.logger = logger.get_logger(__name__)

    # ------------------------
    # HOOKS
    # ------------------------
    def handle_on_voice_state_update_event(self, player_id: str, player_name: str, before_channel: str | None,
                                           after_channel: str | None) -> None:
        """
        Handles the Discord voice state update event
        :param player_id: player id
        :param player_name: player moniker
        :param before_channel: before_state channel name
        :param after_channel: after_state channel name
        :return: None
        """
        self.logger.info(
            f"Player voice state changed, player: {player_id} [{player_name}], from {before_channel} to {after_channel}",
            extra={"player_id": player_id, "before_channel": before_channel,
                   "after_channel": after_channel})
        if player_id not in settings.general.players.keys():
            self.logger.debug(f"Non-tracked player ignored: {player_id} [{player_name}]",
                              extra={"player_id": player_id})
            return
        event = None
        if before_channel is None:
            event = PlayerJoinedSessionEvent(datetime.now(), player_id, datetime.now())
        elif after_channel is None:
            event = PlayerLeftSessionEvent(datetime.now(), player_id, datetime.now())
        else:
            self.logger.debug(f"ignoring channel switch for player: {player_id}", extra={"player_id": player_id})
        if event:
            self.event_bus.publish(event)

    def handle_on_ready_event(self) -> None:
        """
        Handles the Discord on_ready event
        :return: None
        """
        self.logger.info("Application Started and connected to Discord")

    # ------------------------
    # COMMANDS
    # -----------------------

    # ------------------------
    # UI Components Callbacks
    # ------------------------
    def handle_session_type_change_modal_submit(self, session_id: str, new_type: str) -> None:
        """
        Handles the session type change modal submit event
        :param session_id: session id
        :param new_type: new session type
        :return: None
        """
        self.logger.info(f"Session type change requested for session {session_id} to type {new_type}",
                         extra={"session_id": session_id, "new_type": new_type})
        event = SessionTypeChangeEvent(datetime.now(), session_id, new_type)
        self.event_bus.publish(event)

    def handle_session_attendance_edit_modal_submit(self, session_id: str, justifications: dict[str, bool],
                                                    motives: dict[str, str]) -> None:
        """
        Handles the session attendance edit modal submit event
        :param session_id: session id
        :param justifications: player_id -> justified_absence
        :param motives: player_id -> motive
        :return: None
        """
        self.logger.info(f"Session attendance edit requested for session {session_id}",
                         extra={"session_id": session_id, "justifications": justifications, "motives": motives})
        event = SessionAttendanceEditEvent(datetime.now(), session_id, justifications, motives)
        self.event_bus.publish(event)
