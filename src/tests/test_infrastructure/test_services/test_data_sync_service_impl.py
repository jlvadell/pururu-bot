from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, equal_to

from pururu.infrastructure.adapters.google_sheets.entities import AttendanceSheet, ClockingSheet
from pururu.infrastructure.services.data_sync_service_impl import DataSyncServiceImpl


@pytest.fixture
def mock_google_sheets_adapter():
    """Create a mock GoogleSheetsAdapter"""
    return MagicMock()


@pytest.fixture
def service(mock_google_sheets_adapter):
    """Create a DataSyncServiceImpl instance with mocked dependencies"""
    return DataSyncServiceImpl(mock_google_sheets_adapter)


@pytest.fixture
def mock_session():
    """Create a mock session"""
    session = MagicMock()
    session.id = "session123"
    return session


@pytest.mark.unit
@patch('pururu.infrastructure.services.data_sync_service_impl.GoogleSheetsMapper')
def test_sync_session_success(mock_mapper, service, mock_google_sheets_adapter, mock_session):
    """Test sync_session successfully syncs attendance and clocking"""
    # Arrange
    mock_attendance = MagicMock(spec=AttendanceSheet)
    mock_clocking = MagicMock(spec=ClockingSheet)
    mock_mapper.to_attendance.return_value = mock_attendance
    mock_mapper.to_clocking.return_value = mock_clocking
    mock_google_sheets_adapter.upsert_attendance.return_value = 42

    # Act
    service.sync_session(mock_session)

    # Assert
    mock_mapper.to_attendance.assert_called_once_with(mock_session)
    mock_google_sheets_adapter.upsert_attendance.assert_called_once_with(mock_attendance)
    mock_mapper.to_clocking.assert_called_once_with(mock_session, 42)
    mock_google_sheets_adapter.upsert_clocking.assert_called_once_with(mock_clocking)


@pytest.mark.unit
@patch('pururu.infrastructure.services.data_sync_service_impl.GoogleSheetsMapper')
def test_sync_session_uses_game_id_from_attendance(mock_mapper, service, mock_google_sheets_adapter, mock_session):
    """Test sync_session passes game_id from attendance to clocking"""
    # Arrange
    mock_attendance = MagicMock(spec=AttendanceSheet)
    mock_clocking = MagicMock(spec=ClockingSheet)
    mock_mapper.to_attendance.return_value = mock_attendance
    mock_mapper.to_clocking.return_value = mock_clocking
    expected_game_id = 99
    mock_google_sheets_adapter.upsert_attendance.return_value = expected_game_id

    # Act
    service.sync_session(mock_session)

    # Assert
    call_args = mock_mapper.to_clocking.call_args
    assert_that(call_args[0][1], equal_to(expected_game_id))


@pytest.mark.unit
@patch('pururu.infrastructure.services.data_sync_service_impl.GoogleSheetsMapper')
def test_sync_session_raises_on_attendance_error(mock_mapper, service, mock_google_sheets_adapter, mock_session):
    """Test sync_session raises exception when attendance upsert fails"""
    # Arrange
    mock_attendance = MagicMock(spec=AttendanceSheet)
    mock_mapper.to_attendance.return_value = mock_attendance
    mock_google_sheets_adapter.upsert_attendance.side_effect = Exception("Attendance API Error")

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        service.sync_session(mock_session)

    assert_that(str(exc_info.value), equal_to("Attendance API Error"))
    mock_google_sheets_adapter.upsert_clocking.assert_not_called()


@pytest.mark.unit
@patch('pururu.infrastructure.services.data_sync_service_impl.GoogleSheetsMapper')
def test_sync_session_raises_on_clocking_error(mock_mapper, service, mock_google_sheets_adapter, mock_session):
    """Test sync_session raises exception when clocking upsert fails"""
    # Arrange
    mock_attendance = MagicMock(spec=AttendanceSheet)
    mock_clocking = MagicMock(spec=ClockingSheet)
    mock_mapper.to_attendance.return_value = mock_attendance
    mock_mapper.to_clocking.return_value = mock_clocking
    mock_google_sheets_adapter.upsert_attendance.return_value = 42
    mock_google_sheets_adapter.upsert_clocking.side_effect = Exception("Clocking API Error")

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        service.sync_session(mock_session)

    assert_that(str(exc_info.value), equal_to("Clocking API Error"))


@pytest.mark.unit
@patch('pururu.infrastructure.services.data_sync_service_impl.GoogleSheetsMapper')
def test_sync_session_raises_on_mapper_error(mock_mapper, service, mock_google_sheets_adapter, mock_session):
    """Test sync_session raises exception when mapper fails"""
    # Arrange
    mock_mapper.to_attendance.side_effect = Exception("Mapper Error")

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        service.sync_session(mock_session)

    assert_that(str(exc_info.value), equal_to("Mapper Error"))
    mock_google_sheets_adapter.upsert_attendance.assert_not_called()
    mock_google_sheets_adapter.upsert_clocking.assert_not_called()
