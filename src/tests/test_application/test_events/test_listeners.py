from typing import Any
from unittest import mock
from unittest.mock import patch, call

import pytest
from hamcrest import assert_that, equal_to

from pururu.application.events.entities import EventType
from pururu.application.events.entities import (MemberJoinedChannelEvent, MemberLeftChannelEvent, NewGameIntentEvent,
                                                EndGameIntentEvent, GameStartedEvent, GameEndedEvent)
from pururu.application.events.listeners import EventListeners
from pururu.domain.entities import Attendance
from tests.test_application.test_events.test_entities import (member_joined_channel_event, member_left_channel_event,
                                                              new_game_intent_event, end_game_intent_event,
                                                              game_started_event, game_ended_event,
                                                              check_expired_polls_event, finalize_poll_event)
from tests.test_domain.test_entities import attendance, poll


@patch('pururu.application.events.event_system.EventSystem')
@patch('pururu.application.services.pururu_handler.PururuHandler')
def set_up(service_mock, event_mock) -> tuple[dict[EventType, list[Any]], EventListeners]:
    listeners = {}
    for event_type_val in EventType:
        listeners[event_type_val] = []
    event_mock.register_listener.side_effect = lambda event_type, listener: {listeners[event_type].append(listener)}
    return listeners, EventListeners(event_mock, service_mock)


@pytest.mark.parametrize("event_type", list(EventType))
def test_event_type_is_registered(event_type):
    # Given - When
    _, event_listeners = set_up()
    # Then
    event_listeners.event_system.create_event.assert_has_calls([call(event_type)])
    event_listeners.event_system.register_listener.assert_has_calls([call(event_type, mock.ANY)])


@pytest.mark.asyncio
async def test_on_member_joined_channel_ok(member_joined_channel_event: MemberJoinedChannelEvent):
    # Given
    defined_listeners, event_listeners = set_up()
    event_function = defined_listeners[member_joined_channel_event.event_type][0]
    # When
    result = await event_function(member_joined_channel_event)
    # Then
    assert_that(result, equal_to(True))
    event_listeners.pururu_handler.handle_member_joined_channel_event.assert_called_once_with(
        member_joined_channel_event)


@pytest.mark.asyncio
async def test_generic_ko(member_joined_channel_event: MemberJoinedChannelEvent):
    # Given
    defined_listeners, event_listeners = set_up()
    event_listeners.pururu_handler.handle_member_joined_channel_event.side_effect = Exception("test exception")
    event_function = defined_listeners[member_joined_channel_event.event_type][0]
    # When
    result = await event_function(member_joined_channel_event)
    # Then
    assert_that(result, equal_to(False))
    event_listeners.pururu_handler.handle_member_joined_channel_event.assert_called_once_with(
        member_joined_channel_event)


@pytest.mark.asyncio
async def test_on_member_left_channel_ok(member_left_channel_event: MemberLeftChannelEvent):
    # Given
    defined_listeners, event_listeners = set_up()
    event_function = defined_listeners[member_left_channel_event.event_type][0]
    # When
    await event_function(member_left_channel_event)
    # Then
    event_listeners.pururu_handler.handle_member_left_channel_event.assert_called_once_with(member_left_channel_event)


@pytest.mark.asyncio
async def test_on_new_game_intent_ok(new_game_intent_event: NewGameIntentEvent):
    # Given
    defined_listeners, event_listeners = set_up()
    event_function = defined_listeners[new_game_intent_event.event_type][0]
    # When
    await event_function(new_game_intent_event)
    # Then
    event_listeners.pururu_handler.handle_new_game_intent_event.assert_called_once_with(new_game_intent_event)


@pytest.mark.asyncio
async def test_on_end_game_intent_ok(end_game_intent_event: EndGameIntentEvent):
    # Given
    defined_listeners, event_listeners = set_up()
    event_function = defined_listeners[end_game_intent_event.event_type][0]
    # When
    await event_function(end_game_intent_event)
    # Then
    event_listeners.pururu_handler.handle_end_game_intent_event.assert_called_once_with(end_game_intent_event)


@pytest.mark.asyncio
async def test_on_game_started_ok(game_started_event: GameStartedEvent):
    # Given
    defined_listeners, event_listeners = set_up()
    event_function = defined_listeners[game_started_event.event_type][0]
    # When
    await event_function(game_started_event)
    # Then
    event_listeners.pururu_handler.handle_game_started_event.assert_called_once_with(game_started_event)


@pytest.mark.asyncio
async def test_on_game_ended_ok(attendance: Attendance, game_ended_event: GameEndedEvent):
    # Given
    defined_listeners, event_listeners = set_up()
    event_function = defined_listeners[game_ended_event.event_type][0]
    # When
    await event_function(game_ended_event)
    # Then
    event_listeners.pururu_handler.handle_game_ended_event.assert_called_once_with(game_ended_event)


@pytest.mark.asyncio
async def test_on_check_expired_polls_ok(check_expired_polls_event):
    # Given
    defined_listeners, event_listeners = set_up()
    event_function = defined_listeners[check_expired_polls_event.event_type][0]
    # When
    await event_function(check_expired_polls_event)
    # Then
    event_listeners.pururu_handler.handle_check_expired_polls_event.assert_called_once_with(check_expired_polls_event)


@pytest.mark.asyncio
@pytest.mark.usefixtures("poll")
async def test_on_finalize_poll_ok(finalize_poll_event):
    # Given
    defined_listeners, event_listeners = set_up()
    event_function = defined_listeners[finalize_poll_event.event_type][0]
    # When
    await event_function(finalize_poll_event)
    # Then
    event_listeners.pururu_handler.handle_finalize_poll_event.assert_called_once_with(finalize_poll_event)
