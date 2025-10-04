import pytest
from hamcrest import assert_that, equal_to

from pururu.infrastructure.adapters.google_sheets.entities import AttendanceSheet, ClockingSheet


@pytest.fixture
def attendance_sheet():
    return AttendanceSheet(
        session_id="abcd",
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


@pytest.mark.unit
def test_attendance_sheet_to_row(attendance_sheet):
    """Test the to_row_values method of AttendanceSheet."""
    # Arrange
    expected = [
        attendance_sheet.session_id,
        attendance_sheet.description,
        attendance_sheet.date,
        attendance_sheet.absence[0],
        attendance_sheet.unjustified[0],
        attendance_sheet.motives[0],
        attendance_sheet.absence[1],
        attendance_sheet.unjustified[1],
        attendance_sheet.motives[1],
        attendance_sheet.absence[2],
        attendance_sheet.unjustified[2],
        attendance_sheet.motives[2],
    ]
    # Act
    actual = attendance_sheet.to_row_values()
    # Assert
    assert_that(actual, equal_to(expected))


@pytest.mark.unit
def test_clocking_sheet_to_row(clocking_sheet):
    """Test the to_row_values method of ClockingSheet."""
    # Arrange
    expected = [clocking_sheet.game_id] + clocking_sheet.playtimes
    # Act
    actual = clocking_sheet.to_row_values()
    # Assert
    assert_that(actual, equal_to(expected))
