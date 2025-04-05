from datetime import datetime
from unittest.mock import patch

import pytest
from hamcrest import assert_that, equal_to

from pururu.application.events.entities import MemberJoinedChannelEvent, MemberLeftChannelEvent, NewGameIntentEvent, \
    EndGameIntentEvent, GameStartedEvent, GameEndedEvent, EventType, FinalizePollEvent, CheckExpiredPollsEvent
from pururu.domain.entities import Attendance, Poll, MemberAttendance, PollResolutionType
from tests.test_domain.test_entities import attendance, poll


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
    return GameEndedEvent.from_attendance(attendance)


@pytest.fixture
def check_expired_polls_event():
    return CheckExpiredPollsEvent()


@pytest.fixture
@pytest.mark.usefixtures("poll")
def finalize_poll_event(poll: Poll):
    return FinalizePollEvent.from_poll(poll)


@patch("pururu.common.utils.get_current_time_formatted", return_value="2023-08-10")
def test_as_bot_event(utils_mock):
    # Given
    event = MemberJoinedChannelEvent(member="member1", channel="channel", joined_at=datetime(2023, 8, 10, 10))
    # When
    actual = event.as_bot_event()
    # Then
    assert_that(actual.event_type, equal_to(EventType.MEMBER_JOINED_CHANNEL.value))
    assert_that(actual.created_at, equal_to("2023-08-10"))
    assert_that(actual.payload, equal_to(event.__dict__))


def test_member_joined_channel_event_process_payload():
    # Given
    payload = {
        "member": "member1",
        "channel": "channel",
        "joined_at": "2023-08-10T10:00:00",
        "created_at": "2023-08-10"
    }
    # When
    actual = MemberJoinedChannelEvent.process_payload(payload)
    # Then
    assert_that(actual.member, equal_to("member1"))
    assert_that(actual.channel, equal_to("channel"))
    assert_that(actual.joined_at, equal_to(datetime(2023, 8, 10, 10)))
    assert_that(actual.created_at, equal_to("2023-08-10"))


def test_member_left_channel_event_process_payload():
    # Given
    payload = {
        "member": "member1",
        "channel": "channel",
        "left_at": "2023-08-10T11:00:00",
        "created_at": "2023-08-10"
    }
    # When
    actual = MemberLeftChannelEvent.process_payload(payload)
    # Then
    assert_that(actual.member, equal_to("member1"))
    assert_that(actual.channel, equal_to("channel"))
    assert_that(actual.left_at, equal_to(datetime(2023, 8, 10, 11)))
    assert_that(actual.created_at, equal_to("2023-08-10"))


def test_new_game_intent_event_process_payload():
    # Given
    payload = {
        "players": ["member1"],
        "start_time": "2023-08-10T10:00:00",
        "created_at": "2023-08-10"
    }
    # When
    actual = NewGameIntentEvent.process_payload(payload)
    # Then
    assert_that(actual.players, equal_to(["member1"]))
    assert_that(actual.start_time, equal_to(datetime(2023, 8, 10, 10)))
    assert_that(actual.created_at, equal_to("2023-08-10"))


def test_end_game_intent_event_process_payload():
    # Given
    payload = {
        "game_id": 1,
        "players": ["member1"],
        "end_time": "2023-08-10T11:00:00",
        "created_at": "2023-08-10"
    }
    # When
    actual = EndGameIntentEvent.process_payload(payload)
    # Then
    assert_that(actual.game_id, equal_to(1))
    assert_that(actual.players, equal_to(["member1"]))
    assert_that(actual.end_time, equal_to(datetime(2023, 8, 10, 11)))
    assert_that(actual.created_at, equal_to("2023-08-10"))


def test_game_started_event_process_payload():
    # Given
    payload = {
        "game_id": 1,
        "players": ["member1"],
        "created_at": "2023-08-10"
    }
    # When
    actual = GameStartedEvent.process_payload(payload)
    # Then
    assert_that(actual.game_id, equal_to(1))
    assert_that(actual.players, equal_to(["member1"]))
    assert_that(actual.created_at, equal_to("2023-08-10"))


def test_game_ended_event_process_payload():
    # Given
    payload = {
        "game_id": 1,
        "date": "2023-08-11",
        "attendance_event_type": "TYPE",
        "members": [
            {
                "member": "member1",
                "attendance": True,
                "justified": False,
                "motive": ""
            }
        ],
        "created_at": "2023-08-10"
    }
    # When
    actual = GameEndedEvent.process_payload(payload)
    # Then
    assert_that(actual.game_id, equal_to(1))
    assert_that(actual.date, equal_to("2023-08-11"))
    assert_that(actual.attendance_event_type, equal_to("TYPE"))
    assert_that(actual.members, equal_to([{
        "member": "member1",
        "attendance": True,
        "justified": False,
        "motive": ""
    }]))
    assert_that(actual.created_at, equal_to("2023-08-10"))


def test_check_expired_polls_event_process_payload():
    # Given
    payload = {
        "created_at": "2023-08-10"
    }
    # When
    actual = CheckExpiredPollsEvent.process_payload(payload)
    # Then
    assert_that(actual.created_at, equal_to("2023-08-10"))


def test_finalize_poll_event_process_payload():
    # Given
    payload = {
        "question": "question",
        "channel_id": 1,
        "answers": ["a", "b"],
        "results": {"a": 1, "b": 2},
        "duration_hours": 12,
        "expires_at": "expires_at",
        "allow_multiple": True,
        "resolution_type": "resolution_type",
        "message_id": 123,
        "created_at": "2023-08-10"
    }
    # When
    actual = FinalizePollEvent.process_payload(payload)
    # Then
    assert_that(actual.question, equal_to("question"))
    assert_that(actual.channel_id, equal_to(1))
    assert_that(actual.answers, equal_to(["a", "b"]))
    assert_that(actual.results, equal_to({"a": 1, "b": 2}))
    assert_that(actual.duration_hours, equal_to(12))
    assert_that(actual.expires_at, equal_to("expires_at"))
    assert_that(actual.allow_multiple, equal_to(True))
    assert_that(actual.resolution_type, equal_to("resolution_type"))
    assert_that(actual.message_id, equal_to(123))
    assert_that(actual.created_at, equal_to("2023-08-10"))

@patch("pururu.common.utils.get_current_time_formatted", return_value="2023-08-10")
@pytest.mark.usefixtures("attendance")
def test_game_ended_event_from_attendance(attendance: Attendance):
    # When
    actual = GameEndedEvent.from_attendance(attendance)
    # Then
    assert_that(actual.game_id, equal_to(attendance.game_id))
    assert_that(actual.date, equal_to(attendance.date))
    assert_that(actual.attendance_event_type, equal_to(attendance.event_type.value))
    assert_that(actual.members, equal_to([
            {
                "member": m.member,
                "attendance": m.attendance,
                "justified": m.justified,
                "motive": m.motive
            }
            for m in attendance.members
        ]))
    assert_that(actual.created_at, equal_to("2023-08-10"))


@patch("pururu.common.utils.get_current_time_formatted", return_value="2023-08-10")
@pytest.mark.usefixtures("attendance")
def test_game_ended_event_to_attendance(utils_mock, attendance: Attendance):
    # Given
    event = GameEndedEvent.from_attendance(attendance)
    # When
    actual = event.to_attendance()
    # Then
    assert_that(actual, equal_to(attendance))


@patch("pururu.common.utils.get_current_time_formatted", return_value="2023-08-10")
@pytest.mark.usefixtures("poll")
def test_finalize_poll_event_from_poll(utils_mock, poll: Poll):
    # When
    actual = FinalizePollEvent.from_poll(poll)
    # Then
    assert_that(actual.question, equal_to(poll.question))
    assert_that(actual.channel_id, equal_to(poll.channel_id))
    assert_that(actual.answers, equal_to(poll.answers))
    assert_that(actual.results, equal_to(poll.results))
    assert_that(actual.duration_hours, equal_to(poll.duration_hours))
    assert_that(actual.expires_at, equal_to(poll.expires_at))
    assert_that(actual.allow_multiple, equal_to(poll.allow_multiple))
    assert_that(actual.resolution_type, equal_to(poll.resolution_type.value))
    assert_that(actual.message_id, equal_to(poll.message_id))

@patch("pururu.common.utils.get_current_time_formatted", return_value="2023-08-10")
@pytest.mark.usefixtures("poll")
def test_finalize_poll_event_to_poll(utils_mock, poll: Poll):
    # Given
    event = FinalizePollEvent.from_poll(poll)
    # When
    actual = event.to_poll()
    # Then
    assert_that(actual, equal_to(poll))