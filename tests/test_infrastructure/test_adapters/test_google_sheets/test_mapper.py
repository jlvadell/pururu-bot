import pytest
from hamcrest import assert_that, equal_to, is_not

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
    assert_that(actual.event_type, equal_to(bot_event_sheet.event_type))
    assert_that(actual.date, equal_to(bot_event_sheet.date))
    assert_that(actual.description, equal_to(bot_event_sheet.description))


@pytest.mark.usefixtures("attendance", "attendance_sheet")
def test_attendance_to_sheet(attendance: Attendance, attendance_sheet: AttendanceSheet):
    actual = mapper.attendance_to_sheet(attendance)
    assert_that(actual.game_id, equal_to(attendance_sheet.game_id))
    assert_that(actual.absence, equal_to(attendance_sheet.absence))
    assert_that(actual.unjustified, equal_to(attendance_sheet.unjustified))
    assert_that(actual.motives, equal_to(attendance_sheet.motives))
    assert_that(actual.date, equal_to(attendance_sheet.date))
    assert_that(actual.description, equal_to(attendance_sheet.description))


@pytest.mark.usefixtures("clocking", "clocking_sheet")
def test_clocking_to_sheet(clocking: Clocking, clocking_sheet: ClockingSheet):
    actual = mapper.clocking_to_sheet(clocking)
    assert_that(actual.member, equal_to(clocking_sheet.member))
    assert_that(actual.game_id, equal_to(clocking_sheet.game_id))
    assert_that(actual.clock_in, equal_to(clocking_sheet.clock_in))
    assert_that(actual.clock_out, equal_to(clocking_sheet.clock_out))


@pytest.mark.usefixtures("attendance_sheet", "attendance")
@patch("config.GS_ATTENDANCE_PLAYER_MAPPING", {"member1": "C", "member2": "F", "member3": "I"})
def test_sheet_to_attendance(attendance_sheet: AttendanceSheet, attendance: Attendance):
    actual = mapper.sheet_to_attendance(attendance_sheet)
    assert_that(actual.game_id, equal_to(attendance.game_id))
    for idx, member in enumerate(attendance.members):
        assert_that(actual.members[idx].member, equal_to(member.member))
        assert_that(actual.members[idx].attendance, equal_to(member.attendance))
        assert_that(actual.members[idx].justified, equal_to(member.justified))
        assert_that(actual.members[idx].motive, equal_to(member.motive))
    assert_that(actual.date, equal_to(attendance.date))
    assert_that(actual.description, equal_to(attendance.description))


@pytest.mark.usefixtures("attendance_sheet")
@patch("config.GS_ATTENDANCE_PLAYER_MAPPING", {"member1": "C", "member2": "F", "member3": "I"})
def test_gs_to_attendance_sheet(attendance_sheet: AttendanceSheet):
    row = attendance_sheet.to_row_values()
    actual = mapper.gs_to_attendance_sheet(attendance_sheet.game_id, row)
    assert_that(actual.game_id, equal_to(attendance_sheet.game_id))
    assert_that(actual.absence, equal_to(attendance_sheet.absence))
    assert_that(actual.unjustified, equal_to(attendance_sheet.unjustified))
    assert_that(actual.motives, equal_to(attendance_sheet.motives))
    assert_that(actual.date, equal_to(attendance_sheet.date))
    assert_that(actual.description, equal_to(attendance_sheet.description))

@pytest.mark.usefixtures("attendance_sheet")
@patch("config.GS_ATTENDANCE_PLAYER_MAPPING", {"member1": "C", "member2": "F", "member3": "I"})
def test_gs_to_attendance_sheet_empty_motive_column(attendance_sheet: AttendanceSheet):
    row = attendance_sheet.to_row_values()
    row.pop()
    actual = mapper.gs_to_attendance_sheet(attendance_sheet.game_id, row)
    assert_that(actual.game_id, equal_to(attendance_sheet.game_id))
    assert_that(actual.absence, equal_to(attendance_sheet.absence))
    assert_that(actual.unjustified, equal_to(attendance_sheet.unjustified))
    assert_that(actual.motives, equal_to(attendance_sheet.motives))
    assert_that(actual.date, equal_to(attendance_sheet.date))
    assert_that(actual.description, equal_to(attendance_sheet.description))


def test_parse_str_to_bool():
    assert_that(mapper.__parse_str_to_bool('FALSE'))
    assert_that(mapper.__parse_str_to_bool('TRUE'), is_not(True))


def test_parse_bool_to_str():
    assert_that(mapper.__parse_bool_to_str(True), equal_to("FALSE"))
    assert_that(mapper.__parse_bool_to_str(False), equal_to("TRUE"))


def test_column_to_index():
    assert_that(mapper.__column_to_index("F"), equal_to(5))


def test_index_to_column():
    assert_that(mapper.__index_to_column(5), equal_to("F"))
