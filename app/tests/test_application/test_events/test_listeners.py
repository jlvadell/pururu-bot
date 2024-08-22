from unittest import mock
from unittest.mock import patch, call

from application.events.entities import MemberJoinedChannelEvent, MemberLeftChannelEvent, NewGameIntentEvent, \
    EndGameIntentEvent, GameStartedEvent, GameEndedEvent
from application.events.event_system import EventType
from application.events.listeners import EventListeners
from domain.entities import Attendance
from tests.test_application.test_events.test_entities import member_joined_channel_event, member_left_channel_event, \
    new_game_intent_event, end_game_intent_event, game_started_event, game_ended_event
from app.tests.test_domain.test_entities import attendance


@patch('application.events.event_system.EventSystem')
@patch('domain.services.pururu_service.PururuService')
def set_up(event_type: EventType, service_mock, event_mock) -> EventListeners:
    listener = EventListeners(service_mock, event_mock)
    listener.event_system.create_event.assert_has_calls([call(event_type)])
    listener.event_system.register_listener.assert_has_calls([call(event_type, mock.ANY)])
    return listener


def test_on_member_joined_channel_ok(member_joined_channel_event: MemberJoinedChannelEvent):
    listener = set_up(EventType.MEMBER_JOINED_CHANNEL)
    listener.on_member_joined_channel(member_joined_channel_event)
    listener.pururu_service.register_bot_event.assert_called_once()
    listener.pururu_service.register_new_player.assert_called_once_with(member_joined_channel_event.member)

def test_on_member_left_channel_ok(member_left_channel_event: MemberLeftChannelEvent):
    listener = set_up(EventType.MEMBER_LEFT_CHANNEL)
    listener.on_member_left_channel(member_left_channel_event)
    listener.pururu_service.register_bot_event.assert_called_once()
    listener.pururu_service.remove_player.assert_called_once_with(member_left_channel_event.member)

def test_on_new_game_intent_ok(new_game_intent_event: NewGameIntentEvent):
    listener = set_up(EventType.NEW_GAME_INTENT)
    listener.on_new_game_intent(new_game_intent_event)
    listener.pururu_service.register_bot_event.assert_called_once()
    listener.pururu_service.register_new_game.assert_called_once()

def test_on_end_game_intent_ok(end_game_intent_event: EndGameIntentEvent):
    listener = set_up(EventType.END_GAME_INTENT)
    listener.on_end_game_intent(end_game_intent_event)
    listener.pururu_service.register_bot_event.assert_called_once()
    listener.pururu_service.end_game.assert_called_once()

def test_on_game_started_ok(game_started_event: GameStartedEvent):
    listener = set_up(EventType.GAME_STARTED)
    listener.on_game_started(game_started_event)
    listener.pururu_service.register_bot_event.assert_called_once()


def test_on_game_ended_ok(attendance: Attendance, game_ended_event: GameEndedEvent):
    listener = set_up(EventType.GAME_ENDED)
    listener.on_game_ended(game_ended_event)
    listener.pururu_service.register_bot_event.assert_called_once()
