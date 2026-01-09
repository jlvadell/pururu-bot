from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, equal_to

from pururu.infrastructure.adapters.google_sheets.entities import AttendanceSheet, ClockingSheet
from pururu.infrastructure.adapters.google_sheets.google_sheets_adapter import GoogleSheetsAdapter


@pytest.fixture
def mock_credentials():
    """Create mock credentials"""
    with patch('pururu.infrastructure.adapters.google_sheets.google_sheets_adapter.Credentials') as mock:
        mock.from_service_account_file.return_value = MagicMock()
        yield mock


@pytest.fixture
def mock_gspread():
    """Create mock gspread"""
    with patch('pururu.infrastructure.adapters.google_sheets.google_sheets_adapter.gspread') as mock:
        yield mock


@pytest.fixture
def adapter(mock_credentials, mock_gspread):
    """Create a GoogleSheetsAdapter instance with mocked dependencies"""
    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_gspread.authorize.return_value = mock_client
    mock_client.open_by_key.return_value = mock_spreadsheet
    return GoogleSheetsAdapter("fake_path.json", "fake_spreadsheet_id")


@pytest.mark.unit
def test_upsert_attendance_new_session(adapter):
    """Test upserting attendance for a new session"""
    # Arrange
    adapter.spreadsheet.values_get.return_value = {'values': [['existing_session1'], ['existing_session2']]}
    attendance = AttendanceSheet(
        session_id="new_session",
        game_id=None,
        absence=["FALSE", "TRUE"],
        unjustified=["FALSE", "FALSE"],
        motives=["", ""],
        date="2025-10-01",
        description="Juegueo Oficial"
    )

    # Act
    result = adapter.upsert_attendance(attendance)

    # Assert
    assert_that(result, equal_to(6))  # DATA_ROW_INIT(4) + len(existing sessions)(2)
    adapter.spreadsheet.values_update.assert_called_once()


@pytest.mark.unit
def test_upsert_attendance_empty_session_ids(adapter):
    """Test upserting attendance when spreadsheet contains empty session_id rows"""
    # Arrange
    adapter.spreadsheet.values_get.return_value = {'values': [[], []]}
    attendance = AttendanceSheet(
        session_id="new_session",
        game_id=None,
        absence=["FALSE", "TRUE"],
        unjustified=["FALSE", "FALSE"],
        motives=["", ""],
        date="2025-10-01",
        description="Juegueo Oficial"
    )

    # Act
    result = adapter.upsert_attendance(attendance)

    # Assert
    assert_that(result, equal_to(6))  # DATA_ROW_INIT(4) + len(existing sessions, no ids)(2)
    adapter.spreadsheet.values_update.assert_called_once()


@pytest.mark.unit
def test_upsert_attendance_existing_session(adapter):
    """Test upserting attendance for an existing session"""
    # Arrange
    adapter.spreadsheet.values_get.return_value = {'values': [['session1'], ['existing_session'], ['session3']]}
    attendance = AttendanceSheet(
        session_id="existing_session",
        game_id=None,
        absence=["FALSE", "TRUE"],
        unjustified=["FALSE", "FALSE"],
        motives=["", ""],
        date="2025-10-01",
        description="Juegueo Oficial"
    )

    # Act
    result = adapter.upsert_attendance(attendance)

    # Assert
    assert_that(result, equal_to(5))  # DATA_ROW_INIT(4) + index(1)
    adapter.spreadsheet.values_update.assert_called_once()


@pytest.mark.unit
def test_upsert_attendance_sets_game_id(adapter):
    """Test upsert_attendance sets game_id on the attendance object"""
    # Arrange
    adapter.spreadsheet.values_get.return_value = {'values': [['session1']]}
    attendance = AttendanceSheet(
        session_id="new_session",
        game_id=None,
        absence=["FALSE"],
        unjustified=["FALSE"],
        motives=[""],
        date="2025-10-01",
        description="Juegueo Oficial"
    )

    # Act
    result = adapter.upsert_attendance(attendance)

    # Assert
    assert_that(attendance.game_id, equal_to(5))
    assert_that(result, equal_to(5))


@pytest.mark.unit
def test_upsert_attendance_raises_on_error(adapter):
    """Test upsert_attendance raises exception when spreadsheet operation fails"""
    # Arrange
    adapter.spreadsheet.values_get.side_effect = Exception("API Error")
    attendance = AttendanceSheet(
        session_id="session1",
        game_id=None,
        absence=["FALSE"],
        unjustified=["FALSE"],
        motives=[""],
        date="2025-10-01",
        description="Juegueo Oficial"
    )

    # Act & Assert
    with pytest.raises(Exception):
        adapter.upsert_attendance(attendance)


@pytest.mark.unit
def test_upsert_clocking_new_game(adapter):
    """Test upserting clocking for a new game_id"""
    # Arrange
    adapter.spreadsheet.values_get.return_value = {'values': [[1], [2]]}
    clocking = ClockingSheet(game_id=3, playtimes=[100, 200, 300])

    # Act
    adapter.upsert_clocking(clocking)

    # Assert
    adapter.spreadsheet.values_update.assert_called_once()
    call_args = adapter.spreadsheet.values_update.call_args
    assert_that('Fichaje!A5:F5' in call_args[1]['range'], equal_to(True))  # DATA_ROW_INIT(3) + len(existing)(2)


@pytest.mark.unit
def test_upsert_clocking_existing_game(adapter):
    """Test upserting clocking for an existing game_id"""
    # Arrange
    adapter.spreadsheet.values_get.return_value = {'values': [[1], [2], [3]]}
    clocking = ClockingSheet(game_id=2, playtimes=[100, 200, 300])

    # Act
    adapter.upsert_clocking(clocking)

    # Assert
    adapter.spreadsheet.values_update.assert_called_once()
    call_args = adapter.spreadsheet.values_update.call_args
    assert_that('Fichaje!A4:F4' in call_args[1]['range'], equal_to(True))  # DATA_ROW_INIT(3) + index(1)


@pytest.mark.unit
def test_upsert_clocking_raises_on_error(adapter):
    """Test upsert_clocking raises exception when spreadsheet operation fails"""
    # Arrange
    adapter.spreadsheet.values_get.side_effect = Exception("API Error")
    clocking = ClockingSheet(game_id=1, playtimes=[100])

    # Act & Assert
    with pytest.raises(Exception):
        adapter.upsert_clocking(clocking)


@pytest.mark.unit
def test_build_data_notation_full_range():
    """Test _build_data_notation with all parameters"""
    # Act
    result = GoogleSheetsAdapter._build_data_notation("Sheet1", "A", 1, "C", 5)

    # Assert
    assert_that(result, equal_to("Sheet1!A1:C5"))


@pytest.mark.unit
def test_build_data_notation_with_row_and_col_end():
    """Test _build_data_notation with row_start and col_end"""
    # Act
    result = GoogleSheetsAdapter._build_data_notation("Sheet1", "A", 1, "C")

    # Assert
    assert_that(result, equal_to("Sheet1!A1:C"))


@pytest.mark.unit
def test_build_data_notation_with_row_only():
    """Test _build_data_notation with only row_start"""
    # Act
    result = GoogleSheetsAdapter._build_data_notation("Sheet1", "A", 1)

    # Assert
    assert_that(result, equal_to("Sheet1!A1"))


@pytest.mark.unit
def test_build_data_notation_column_only():
    """Test _build_data_notation with only column"""
    # Act
    result = GoogleSheetsAdapter._build_data_notation("Sheet1", "A")

    # Assert
    assert_that(result, equal_to("Sheet1!A:A"))
