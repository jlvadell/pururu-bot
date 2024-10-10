from pururu.application.events.entities import MemberJoinedChannelEvent, MemberLeftChannelEvent, NewGameIntentEvent, \
    EndGameIntentEvent, GameStartedEvent, GameEndedEvent, CheckExpiredPollsEvent, EventType
from pururu.application.events.event_system import EventSystem
from pururu.application.services.pururu_handler import PururuHandler
from pururu.utils import get_logger


class EventListeners:
    def __init__(self, event_system: EventSystem, pururu_handler: PururuHandler):
        self.event_system = event_system
        self.pururu_handler = pururu_handler
        self.logger = get_logger(__name__)

        event_system.create_event(EventType.MEMBER_JOINED_CHANNEL)
        event_system.register_listener(EventType.MEMBER_JOINED_CHANNEL, self.on_member_joined_channel)

        event_system.create_event(EventType.MEMBER_LEFT_CHANNEL)
        event_system.register_listener(EventType.MEMBER_LEFT_CHANNEL, self.on_member_left_channel)

        event_system.create_event(EventType.END_GAME_INTENT)
        event_system.register_listener(EventType.END_GAME_INTENT, self.on_end_game_intent)

        event_system.create_event(EventType.NEW_GAME_INTENT)
        event_system.register_listener(EventType.NEW_GAME_INTENT, self.on_new_game_intent)

        event_system.create_event(EventType.GAME_ENDED)
        event_system.register_listener(EventType.GAME_ENDED, self.on_game_ended)

        event_system.create_event(EventType.GAME_STARTED)
        event_system.register_listener(EventType.GAME_STARTED, self.on_game_started)

        event_system.create_event(EventType.CHECK_EXPIRED_POLLS)
        event_system.register_listener(EventType.CHECK_EXPIRED_POLLS, self.on_check_expired_polls)

        event_system.create_event(EventType.FINALIZE_POLL)
        event_system.register_listener(EventType.FINALIZE_POLL, self.on_finalize_poll)

    def on_member_joined_channel(self, data: MemberJoinedChannelEvent):
        try:
            self.pururu_handler.handle_member_joined_channel_event(data)
        except Exception as e:
            self.logger.error(f"Error handling event '{data}': {e}")

    def on_member_left_channel(self, data: MemberLeftChannelEvent):
        try:
            self.pururu_handler.handle_member_left_channel_event(data)
        except Exception as e:
            self.logger.error(f"Error handling event '{data}': {e}")

    def on_new_game_intent(self, data: NewGameIntentEvent):
        try:
            self.pururu_handler.handle_new_game_intent_event(data)
        except Exception as e:
            self.logger.error(f"Error handling event '{data}': {e}")

    def on_end_game_intent(self, data: EndGameIntentEvent):
        try:
            self.pururu_handler.handle_end_game_intent_event(data)
        except Exception as e:
            self.logger.error(f"Error handling event '{data}': {e}")

    def on_game_started(self, data: GameStartedEvent):
        try:
            self.pururu_handler.handle_game_started_event(data)
        except Exception as e:
            self.logger.error(f"Error handling event '{data}': {e}")

    def on_game_ended(self, data: GameEndedEvent):
        try:
            self.pururu_handler.handle_game_ended_event(data)
        except Exception as e:
            self.logger.error(f"Error handling event '{data}': {e}")

    async def on_check_expired_polls(self, data: CheckExpiredPollsEvent):
        try:
            await self.pururu_handler.handle_check_expired_polls_event(data)
        except Exception as e:
            self.logger.error(f"Error handling event '{data}': {e}")

    async def on_finalize_poll(self, data):
        try:
            await self.pururu_handler.handle_finalize_poll_event(data)
        except Exception as e:
            self.logger.error(f"Error handling event '{data}': {e}")
