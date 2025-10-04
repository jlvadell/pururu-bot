from datetime import datetime

from pururu.common import logger
from pururu.config import settings
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import PlayerJoinedSessionEvent, PlayerLeftSessionEvent


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
        self.logger.info(f"Player voice state changed, player: {player_id}, from {before_channel} to {after_channel}",
                         extra={"player_id": player_id, "before_channel": before_channel,
                                "after_channel": after_channel})
        if player_name not in settings.general.players.keys():
            self.logger.debug(f"Non-tracked player ignored: {player_id}", extra={"player_id": player_id})
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
