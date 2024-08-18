import pytest
import infrastructure.adapters.google_sheets.mapper as mapper
from domain.entities import BotEvent, Attendance, Clocking
from infrastructure.adapters.google_sheets.entities import BotEventSheet, AttendanceSheet, ClockingSheet
from tests.test_infrastructure.test_adapters.test_google_sheets.test_entities import bot_event_sheet, \
    attendance_sheet, clocking_sheet
from tests.test_domain.test_entities import bot_event, attendance, clocking
from unittest.mock import patch


@pytest.mark.usefixtures("bot_event", "bot_event_sheet")
def test_bot_event_to_sheet(bot_event: BotEvent, bot_event_sheet: BotEventSheet):
    actual = mapper.bot_event_to_sheet(bot_event)
    assert actual.event_type == bot_event_sheet.event_type
    assert actual.date == bot_event_sheet.date
    assert actual.description == bot_event_sheet.description


@pytest.mark.usefixtures("attendance", "attendance_sheet")
def test_attendance_to_sheet(attendance: Attendance, attendance_sheet: AttendanceSheet):
    actual = mapper.attendance_to_sheet(attendance)
    assert actual.game_id == attendance_sheet.game_id
    assert actual.absence == attendance_sheet.absence
    assert actual.unjustified == attendance_sheet.unjustified
    assert actual.motives == attendance_sheet.motives
    assert actual.date == attendance_sheet.date
    assert actual.description == attendance_sheet.description


@pytest.mark.usefixtures("clocking", "clocking_sheet")
def test_clocking_to_sheet(clocking: Clocking, clocking_sheet: ClockingSheet):
    actual = mapper.clocking_to_sheet(clocking)
    assert actual.member == clocking_sheet.member
    assert actual.game_id == clocking_sheet.game_id
    assert actual.clock_in == clocking_sheet.clock_in
    assert actual.clock_out == clocking_sheet.clock_out


@pytest.mark.usefixtures("attendance_sheet", "attendance")
@patch("config.GS_ATTENDANCE_PLAYER_MAPPING", {"member1": "C", "member2": "F", "member3": "I"})
def test_sheet_to_attendance(attendance_sheet: AttendanceSheet, attendance: Attendance):
    actual = mapper.sheet_to_attendance(attendance_sheet)
    assert actual.game_id == attendance.game_id
    for idx, member in enumerate(attendance.members):
        assert actual.members[idx].member == member.member
        assert actual.members[idx].attendance == member.attendance
        assert actual.members[idx].justified == member.justified
        assert actual.members[idx].motive == member.motive
    assert actual.date == attendance.date
    assert actual.description == attendance.description


@pytest.mark.usefixtures("attendance_sheet")
@patch("config.GS_ATTENDANCE_PLAYER_MAPPING", {"member1": "C", "member2": "F", "member3": "I"})
def test_gs_to_attendance_sheet(attendance_sheet: AttendanceSheet):
    row = attendance_sheet.to_row_values()
    actual = mapper.gs_to_attendance_sheet(attendance_sheet.game_id, row)
    assert actual.game_id == attendance_sheet.game_id
    assert actual.absence == attendance_sheet.absence
    assert actual.unjustified == attendance_sheet.unjustified
    assert actual.motives == attendance_sheet.motives
    assert actual.date == attendance_sheet.date
    assert actual.description == attendance_sheet.description

@pytest.mark.usefixtures("attendance_sheet")
@patch("config.GS_ATTENDANCE_PLAYER_MAPPING", {"member1": "C", "member2": "F", "member3": "I"})
def test_gs_to_attendance_sheet_empty_motive_column(attendance_sheet: AttendanceSheet):
    row = attendance_sheet.to_row_values()
    row.pop()
    actual = mapper.gs_to_attendance_sheet(attendance_sheet.game_id, row)
    assert actual.game_id == attendance_sheet.game_id
    assert actual.absence == attendance_sheet.absence
    assert actual.unjustified == attendance_sheet.unjustified
    assert actual.motives == attendance_sheet.motives
    assert actual.date == attendance_sheet.date
    assert actual.description == attendance_sheet.description


def test_parse_str_to_bool():
    assert mapper.__parse_str_to_bool('FALSE') is True
    assert mapper.__parse_str_to_bool('TRUE') is False


def test_parse_bool_to_str():
    assert mapper.__parse_bool_to_str(True) == "FALSE"
    assert mapper.__parse_bool_to_str(False) == "TRUE"


def test_column_to_index():
    assert mapper.__column_to_index("F") == 5


def test_index_to_column():
    assert mapper.__index_to_column(5) == "F"
