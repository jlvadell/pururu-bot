from unittest.mock import patch

import pytest
from hamcrest import assert_that, equal_to

from pururu.application.events.entities import MemberJoinedChannelEvent, MemberLeftChannelEvent, NewGameIntentEvent, \
    EndGameIntentEvent, GameStartedEvent, GameEndedEvent
from pururu.application.events.event_system import EventType
from pururu.domain.entities import Attendance
from tests.test_domain.test_entities import attendance


@pytest.fixture
def member_joined_channel_event():
    return MemberJoinedChannelEvent(
        member="member1",
        channel="channel",
    )


@pytest.fixture
def member_left_channel_event():
    return MemberLeftChannelEvent(
        member="member1",
        channel="channel",
    )


@pytest.fixture
def new_game_intent_event():
    return NewGameIntentEvent(
        players=["member1"],
    )


@pytest.fixture
def end_game_intent_event():
    return EndGameIntentEvent(
        game_id="1",
        players=["member1"],
    )


@pytest.fixture
def game_started_event():
    return GameStartedEvent(
        game_id="1",
        players=["member1"],
    )


@pytest.fixture
@pytest.mark.usefixtures("attendance")
def game_ended_event(attendance: Attendance):
    return GameEndedEvent(
        attendance=attendance,
    )


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_member_joined_channel_event_as_bot_event(utils_mock, member_joined_channel_event: MemberJoinedChannelEvent):
    actual = member_joined_channel_event.as_bot_event()
    assert_that(actual.event_type, equal_to(EventType.MEMBER_JOINED_CHANNEL.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("member member1 has joined channel channel"))


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_member_left_channel_event_as_bot_event(utils_mock, member_left_channel_event: MemberLeftChannelEvent):
    actual = member_left_channel_event.as_bot_event()
    assert_that(actual.event_type, equal_to(EventType.MEMBER_LEFT_CHANNEL.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("member member1 has left channel channel"))


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_new_game_intent_event_as_bot_event(utils_mock, new_game_intent_event: NewGameIntentEvent):
    actual = new_game_intent_event.as_bot_event()
    assert_that(actual.event_type, equal_to(EventType.NEW_GAME_INTENT.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("players: ['member1']"))


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_end_game_intent_event_as_bot_event(utils_mock, end_game_intent_event: EndGameIntentEvent):
    actual = end_game_intent_event.as_bot_event()
    assert_that(actual.event_type, equal_to(EventType.END_GAME_INTENT.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("game_id: 1, players: ['member1']"))


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_game_started_event_as_bot_event(utils_mock, game_started_event: GameStartedEvent):
    actual = game_started_event.as_bot_event()
    assert_that(actual.event_type, equal_to(EventType.GAME_STARTED.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("game_id: 1, players: ['member1']"))


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_game_ended_event_as_bot_event(utils_mock, game_ended_event: GameEndedEvent):
    actual = game_ended_event.as_bot_event()
    assert_that(actual.event_type, equal_to(EventType.GAME_ENDED.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("game_id: 1, attended: ['member1'], absences: ['member2', 'member3']"))
