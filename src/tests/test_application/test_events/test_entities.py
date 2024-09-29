from datetime import datetime
from unittest.mock import patch

import pytest
from hamcrest import assert_that, equal_to

from pururu.application.events.entities import MemberJoinedChannelEvent, MemberLeftChannelEvent, NewGameIntentEvent, \
    EndGameIntentEvent, GameStartedEvent, GameEndedEvent, EventType
from pururu.domain.entities import Attendance
from tests.test_domain.test_entities import attendance


@pytest.fixture
def member_joined_channel_event():
    return MemberJoinedChannelEvent(
        member="member1",
        channel="channel",
        joined_at=datetime(2023, 8, 10, 10),
    )


@pytest.fixture
def member_left_channel_event():
    return MemberLeftChannelEvent(
        member="member1",
        channel="channel",
        left_at=datetime(2023, 8, 10, 11),
    )


@pytest.fixture
def new_game_intent_event():
    return NewGameIntentEvent(
        players=["member1"],
        start_time=datetime(2023, 8, 10, 10),
    )


@pytest.fixture
def end_game_intent_event():
    return EndGameIntentEvent(
        game_id=1,
        players=["member1"],
        end_time=datetime(2023, 8, 10, 11),
    )


@pytest.fixture
def game_started_event():
    return GameStartedEvent(
        game_id=1,
        players=["member1"],
    )


@pytest.fixture
@pytest.mark.usefixtures("attendance")
def game_ended_event(attendance: Attendance):
    return GameEndedEvent(
        attendance=attendance,
    )


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_member_joined_channel_event_as_bot_event(utils_mock):
    # Given
    member_joined_channel_event = MemberJoinedChannelEvent(member="member1", channel="channel",
                                                           joined_at=datetime(2023, 8, 10, 10))
    # When
    actual = member_joined_channel_event.as_bot_event()
    # Then
    assert_that(actual.event_type, equal_to(EventType.MEMBER_JOINED_CHANNEL.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("member member1 has joined channel channel at 2023-08-10 10:00:00"))


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_member_left_channel_event_as_bot_event(utils_mock):
    # Given
    member_left_channel_event = MemberLeftChannelEvent(member="member1", channel="channel",
                                                       left_at=datetime(2023, 8, 10, 11))
    # When
    actual = member_left_channel_event.as_bot_event()
    # Then
    assert_that(actual.event_type, equal_to(EventType.MEMBER_LEFT_CHANNEL.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("member member1 has left channel channel at 2023-08-10 11:00:00"))


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_new_game_intent_event_as_bot_event(utils_mock):
    # Given
    new_game_intent_event = NewGameIntentEvent(players=["member1"], start_time=datetime(2023, 8, 10, 10))
    # When
    actual = new_game_intent_event.as_bot_event()
    # Then
    assert_that(actual.event_type, equal_to(EventType.NEW_GAME_INTENT.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("players: ['member1'], start_time 2023-08-10 10:00:00"))


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_end_game_intent_event_as_bot_event(utils_mock):
    # Given
    end_game_intent_event = EndGameIntentEvent(game_id=1, players=["member1"], end_time=datetime(2023, 8, 10, 11))
    # When
    actual = end_game_intent_event.as_bot_event()
    # Then
    assert_that(actual.event_type, equal_to(EventType.END_GAME_INTENT.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("game_id: 1, players: ['member1'], end_time 2023-08-10 11:00:00"))


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_game_started_event_as_bot_event(utils_mock):
    # Given
    game_started_event = GameStartedEvent(game_id=1, players=["member1"])
    # When
    actual = game_started_event.as_bot_event()
    # Then
    assert_that(actual.event_type, equal_to(EventType.GAME_STARTED.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("game_id: 1, players: ['member1']"))


@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_game_ended_event_as_bot_event(utils_mock, attendance: Attendance):
    # Given
    game_ended_event = GameEndedEvent(attendance=attendance)
    # When
    actual = game_ended_event.as_bot_event()
    # Then
    assert_that(actual.event_type, equal_to(EventType.GAME_ENDED.value))
    assert_that(actual.date, equal_to("2023-08-10"))
    assert_that(actual.description, equal_to("game_id: 1, attended: ['member1'], absences: ['member2', 'member3']"))
