from unittest import mock
from unittest.mock import patch, call

import pytest

from pururu.application.events.entities import MemberJoinedChannelEvent, MemberLeftChannelEvent, NewGameIntentEvent, \
    EndGameIntentEvent, GameStartedEvent, GameEndedEvent
from pururu.application.events.event_system import EventType
from pururu.application.events.listeners import EventListeners
from pururu.domain.entities import Attendance
from tests.test_application.test_events.test_entities import member_joined_channel_event, member_left_channel_event, \
    new_game_intent_event, end_game_intent_event, game_started_event, game_ended_event
from tests.test_domain.test_entities import attendance


@patch('pururu.application.events.event_system.EventSystem')
@patch('pururu.domain.services.pururu_service.PururuService')
def set_up(service_mock, event_mock) -> EventListeners:
    return EventListeners(service_mock, event_mock)


@pytest.mark.parametrize("event_type", list(EventType))
def test_event_type_is_registered(event_type):
    # Given - When
    listener = set_up()
    # Then
    listener.event_system.create_event.assert_has_calls([call(event_type)])
    listener.event_system.register_listener.assert_has_calls([call(event_type, mock.ANY)])


def test_on_member_joined_channel_ok(member_joined_channel_event: MemberJoinedChannelEvent):
    # Given
    listener = set_up()
    # When
    listener.on_member_joined_channel(member_joined_channel_event)
    # Then
    listener.pururu_service.register_bot_event.assert_called_once()
    listener.pururu_service.register_new_player.assert_called_once_with(member_joined_channel_event.member)


def test_on_member_left_channel_ok(member_left_channel_event: MemberLeftChannelEvent):
    # Given
    listener = set_up()
    # When
    listener.on_member_left_channel(member_left_channel_event)
    # Then
    listener.pururu_service.register_bot_event.assert_called_once()
    listener.pururu_service.remove_player.assert_called_once_with(member_left_channel_event.member)


def test_on_new_game_intent_ok(new_game_intent_event: NewGameIntentEvent):
    # Given
    listener = set_up()
    # When
    listener.on_new_game_intent(new_game_intent_event)
    # Then
    listener.pururu_service.register_bot_event.assert_called_once()
    listener.pururu_service.register_new_game.assert_called_once_with(new_game_intent_event.start_time)


def test_on_end_game_intent_ok(end_game_intent_event: EndGameIntentEvent):
    # Given
    listener = set_up()
    # When
    listener.on_end_game_intent(end_game_intent_event)
    # Then
    listener.pururu_service.register_bot_event.assert_called_once()
    listener.pururu_service.end_game.assert_called_once_with(end_game_intent_event.end_time)


def test_on_game_started_ok(game_started_event: GameStartedEvent):
    # Given
    listener = set_up()
    # When
    listener.on_game_started(game_started_event)
    # Then
    listener.pururu_service.register_bot_event.assert_called_once()


def test_on_game_ended_ok(attendance: Attendance, game_ended_event: GameEndedEvent):
    # Given
    listener = set_up()
    # When
    listener.on_game_ended(game_ended_event)
    # Then
    listener.pururu_service.register_bot_event.assert_called_once()
