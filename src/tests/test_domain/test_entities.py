import pytest
from hamcrest import assert_that, equal_to

from pururu.domain.entities import BotEvent, Attendance, MemberAttendance, Clocking, AttendanceEventType


@pytest.fixture
def bot_event():
    return BotEvent(
        event_type="event_type",
        date="2023-08-10",
        description="Bot event description"
    )


def member1():
    return MemberAttendance(
        member="member1",
        attendance=True,
        justified=True,
        motive="personal"
    )


def member2():
    return MemberAttendance(
        member="member2",
        attendance=False,
        justified=True,
        motive="personal"
    )


def member3():
    return MemberAttendance(
        member="member3",
        attendance=False,
        justified=False,
        motive=""
    )


@pytest.fixture
def member_attendance_ok():
    return member1()


@pytest.fixture
def member_attendance_absence_justified():
    return member2()


@pytest.fixture
def member_attendance_absence():
    return member3()


@pytest.fixture
def attendance():
    return Attendance(
        game_id=1,
        members=[member1(), member2(), member3()],
        date="2023-08-10",
        event_type=AttendanceEventType.OFFICIAL_GAME
    )


@pytest.fixture
def clocking():
    return Clocking(
        game_id=1,
        playtimes=[300, 0, 1800]
    )


@pytest.mark.parametrize("event, expected", [
    ("Juegueo Oficial", AttendanceEventType.OFFICIAL_GAME),
    ("Juegueo Adicional Oficial", AttendanceEventType.ADDITIONAL_OFFICIAL_GAME),
    ("Quedada Oficial", AttendanceEventType.OFFICIAL_MEETING),
    ("random_type123456", AttendanceEventType.UNKNOWN),
    ("", AttendanceEventType.UNKNOWN),
    (None, AttendanceEventType.UNKNOWN)
])
def test_attendance_event_type_of_test_cases(event: str, expected: AttendanceEventType):
    actual = AttendanceEventType.of(event)
    assert_that(actual, equal_to(expected))