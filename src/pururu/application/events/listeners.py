from pururu.application.events.entities import MemberJoinedChannelEvent, MemberLeftChannelEvent, NewGameIntentEvent, \
    EndGameIntentEvent, GameStartedEvent, GameEndedEvent

from pururu.application.events.event_system import EventSystem, EventType
from pururu.domain.services.pururu_service import PururuService
from pururu.utils import get_logger


class EventListeners:
    def __init__(self, event_system: EventSystem, pururu_service: PururuService):
        self.event_system = event_system
        self.pururu_service = pururu_service
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

    def on_member_joined_channel(self, data: MemberJoinedChannelEvent):
        self.logger.info(
            f"Handling event '{EventType.MEMBER_JOINED_CHANNEL}' member {data.member} joined {data.channel} Channel")
        self.pururu_service.register_bot_event(data.as_bot_event())
        self.pururu_service.register_new_player(data.member)

    def on_member_left_channel(self, data: MemberLeftChannelEvent):
        self.logger.info(
            f"Handling event '{EventType.MEMBER_LEFT_CHANNEL}' member {data.member} left {data.channel} Channel")
        self.pururu_service.register_bot_event(data.as_bot_event())
        self.pururu_service.remove_player(data.member)

    def on_new_game_intent(self, data: NewGameIntentEvent):
        self.logger.info(f"Handling event '{EventType.NEW_GAME_INTENT}' possible new game with players: {data.players}")
        self.pururu_service.register_bot_event(data.as_bot_event())
        self.pururu_service.register_new_game()

    def on_end_game_intent(self, data: EndGameIntentEvent):
        self.logger.info(f"Handling event '{EventType.END_GAME_INTENT}' game {data.game_id} players {data.players}")
        self.pururu_service.register_bot_event(data.as_bot_event())
        self.pururu_service.end_game()

    def on_game_started(self, data: GameStartedEvent):
        self.logger.info(f"Handling event '{EventType.GAME_STARTED}' new game started; "
                         f"id {data.game_id}, players {data.players}")
        self.pururu_service.register_bot_event(data.as_bot_event())

    def on_game_ended(self, data: GameEndedEvent):
        self.logger.info(f"Handling event '{EventType.GAME_ENDED}' game {data.attendance.game_id} ended")
        self.pururu_service.register_bot_event(data.as_bot_event())
