from datetime import datetime

from pururu.common import logger
from pururu.config import settings
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.secondary_events import CheckExpiredPollsEvent


class BackgroundEventHandler:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.logger = logger.get_logger(__name__)

    # ---------------------------
    # TIMED JOBS
    # ---------------------------

    def trigger_check_expired_polls_flow(self) -> None:
        """
        Triggers the flow to check for expired polls
        :return: None
        """
        self.logger.debug("Emitting CheckExpiredPollsEvent")
        self.event_bus.publish(CheckExpiredPollsEvent(datetime.now()))

    # ---------------------------
    # WATCHDOG EVENTS
    # ---------------------------
    def on_configuration_files_changed(self) -> None:
        """
        Handles the configuration files changed event.
        This method is called when the configuration files are changed.
        :return: None
        """
        self.logger.debug("Reloading settings")
        settings.reload()
        self.logger.debug("Recreating logger with new settings")
        logger.reset_logging()
        self.logger.debug("Settings reloaded successfully")
