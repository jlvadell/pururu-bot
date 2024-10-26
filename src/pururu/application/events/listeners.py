import inspect

from pururu.application.events.entities import (PururuEvent, EventType)
from pururu.application.events.event_system import EventSystem
from pururu.application.services.pururu_handler import PururuHandler
from common.utils import get_logger


class EventListeners:
    def __init__(self, event_system: EventSystem, pururu_handler: PururuHandler):
        self.event_system = event_system
        self.pururu_handler = pururu_handler
        self.logger = get_logger(__name__)

        event_system.create_event(EventType.MEMBER_JOINED_CHANNEL)
        event_system.register_listener(EventType.MEMBER_JOINED_CHANNEL,
                                       lambda event: self._event_listener(event,
                                                                          self.pururu_handler.handle_member_joined_channel_event))

        event_system.create_event(EventType.MEMBER_LEFT_CHANNEL)
        event_system.register_listener(EventType.MEMBER_LEFT_CHANNEL,
                                       lambda event: self._event_listener(event,
                                                                          self.pururu_handler.handle_member_left_channel_event))

        event_system.create_event(EventType.END_GAME_INTENT)
        event_system.register_listener(EventType.END_GAME_INTENT,
                                       lambda event: self._event_listener(event,
                                                                          self.pururu_handler.handle_end_game_intent_event))

        event_system.create_event(EventType.NEW_GAME_INTENT)
        event_system.register_listener(EventType.NEW_GAME_INTENT,
                                       lambda event: self._event_listener(event,
                                                                          self.pururu_handler.handle_new_game_intent_event))

        event_system.create_event(EventType.GAME_ENDED)
        event_system.register_listener(EventType.GAME_ENDED,
                                       lambda event: self._event_listener(event,
                                                                          self.pururu_handler.handle_game_ended_event))

        event_system.create_event(EventType.GAME_STARTED)
        event_system.register_listener(EventType.GAME_STARTED,
                                       lambda event: self._event_listener(event,
                                                                          self.pururu_handler.handle_game_started_event))

        event_system.create_event(EventType.CHECK_EXPIRED_POLLS)
        event_system.register_listener(EventType.CHECK_EXPIRED_POLLS,
                                       lambda event: self._event_listener(event,
                                                                          self.pururu_handler.handle_check_expired_polls_event))

        event_system.create_event(EventType.FINALIZE_POLL)
        event_system.register_listener(EventType.FINALIZE_POLL,
                                       lambda event: self._event_listener(event,
                                                                          self.pururu_handler.handle_finalize_poll_event))

    async def _event_listener(self, data: PururuEvent, handler) -> bool:
        """
        Generic event listener, calls the handler with the data then returns True if the event was handled successfully
        False otherwise.
        :param data: a pururu event
        :param handler: the handler for the event
        :return: bool: True if the event was handled successfully, False otherwise
        """
        try:
            if inspect.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)
            return True
        except Exception as e:
            self.logger.error(f"Error handling event '{data}': {e}")
            return False
