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
    # Act
    actual = attendance_sheet.to_row_values()
    # Assert
    assert_that(actual, equal_to(["abcd", "Juegueo Oficial", "2023-08-10", "FALSE", "FALSE", "personal", "TRUE",
                                  "FALSE", "personal", "TRUE", "TRUE", ""]))


@pytest.mark.unit
def test_clocking_sheet_to_row(clocking_sheet):
    """Test the to_row_values method of ClockingSheet."""
    # Act
    actual = clocking_sheet.to_row_values()
    # Assert
    assert_that(actual, equal_to([1, 300, 0, 1800]))
