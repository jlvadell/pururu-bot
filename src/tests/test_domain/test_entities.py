import pytest
from pururu.domain.entities import BotEvent, Attendance, MemberAttendance, Clocking


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
        description="Attendance description"
    )


@pytest.fixture
def clocking():
    return Clocking(
        member="member",
        game_id=1,
        clock_in="2023-08-10 10:00:00",
        clock_out="2023-08-10 12:00:00"
    )
