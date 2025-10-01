import pytest
from hamcrest import assert_that, equal_to

from pururu.infrastructure.adapters.google_sheets.entities import AttendanceSheet, BotEventSheet, ClockingSheet


@pytest.fixture
def bot_event_sheet():
    return BotEventSheet(
        event_type="event_type",
        date="2023-08-10",
        description="Bot event description"
    )


@pytest.fixture
def attendance_sheet():
    return AttendanceSheet(
        game_id=1,
        absence=["FALSE", "TRUE", "TRUE"],
        unjustified=["FALSE", "FALSE", "TRUE"],
        motives=["personal", "personal", ""],
        date="2023-08-10",
        description="Juegueo Oficial"
    )


@pytest.fixture
def clocking_sheet():
    return ClockingSheet(
        game_id=1,
        playtimes=[300, 0, 1800]
    )


@pytest.mark.usefixtures("bot_event_sheet")
def test_bot_event_sheet_to_row(bot_event_sheet: BotEventSheet):
    actual = bot_event_sheet.to_row_values()
    assert_that(actual, equal_to(["event_type", "2023-08-10", "Bot event description"]))


@pytest.mark.usefixtures("attendance_sheet")
def test_attendance_sheet_to_row(attendance_sheet: AttendanceSheet):
    actual = attendance_sheet.to_row_values()
    assert_that(actual, equal_to(["Juegueo Oficial", "2023-08-10", "FALSE", "FALSE", "personal", "TRUE",
                                  "FALSE", "personal", "TRUE", "TRUE", ""]))


@pytest.mark.usefixtures("clocking_sheet")
def test_clocking_sheet_to_row(clocking_sheet: ClockingSheet):
    actual = clocking_sheet.to_row_values()
    assert_that(actual, equal_to([1, 300, 0, 1800]))
