import pytest
from hamcrest import assert_that, has_length, equal_to, raises

from pururu.domain.entities import Attendance, Clocking, BotEvent
from pururu.infrastructure.adapters.google_sheets.entities import AttendanceSheet, ClockingSheet, BotEventSheet, \
    CoinsSheet
from tests.test_domain.test_entities import attendance, clocking, bot_event
from tests.test_infrastructure.test_adapters.test_google_sheets.test_entities import attendance_sheet, clocking_sheet, \
    bot_event_sheet
from pururu.infrastructure.adapters.google_sheets.google_sheets_adapter import GoogleSheetsAdapter

from unittest.mock import patch, Mock, MagicMock


@patch('pururu.infrastructure.adapters.google_sheets.google_sheets_adapter.gspread')
@patch('google.oauth2.service_account.Credentials.from_service_account_file')
@patch('pururu.common.circuit_breaker.CircuitBreaker')
def set_up(gspread_mock, credentials_mock, circuit_breaker_mock) -> GoogleSheetsAdapter:
    gs_client_mock = Mock()
    gspread_mock.authorize.return_value = gs_client_mock
    gs_client_mock.open_by_key.return_value = gs_client_mock
    circuit_breaker_mock.call.side_effect = lambda x, *y, **z: x(*y, **z)
    adapter = GoogleSheetsAdapter('credentials.json', 'spreadsheet_id')
    adapter.circuit_breaker = circuit_breaker_mock
    return adapter


@patch('pururu.infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
@pytest.mark.usefixtures("attendance", "attendance_sheet")
def test_upsert_attendance_ok(mapper_mock, attendance: Attendance, attendance_sheet: AttendanceSheet):
    # Given
    adapter = set_up()
    mapper_mock.attendance_to_sheet.return_value = attendance_sheet
    # When
    adapter.upsert_attendance(attendance)
    # Then
    adapter.spreadsheet.values_update.assert_called_with(
        range=f"{AttendanceSheet.SHEET}!{AttendanceSheet.DATA_COL_INIT}{attendance_sheet.game_id}:"
              f"{AttendanceSheet.DATA_COL_END}{attendance_sheet.game_id}",
        params=adapter.DEFAULT_PARAMS, body={"values": [attendance_sheet.to_row_values()]}
    )
    adapter.circuit_breaker.call.assert_called()


@patch('pururu.infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
def test_upsert_clocking_game_id_exists(mapper_mock, clocking: Clocking, clocking_sheet: ClockingSheet):
    # Given
    adapter = set_up()
    adapter.spreadsheet.values_get.return_value = {
        'values': [
            [clocking.game_id - 1], # Actual idx = idx + starting row = 0 + 3 = 3
            [clocking.game_id], # Actual idx = idx + starting row = 1 + 3 = 4
            [clocking.game_id + 1]]} # Actual idx = idx + starting row = 2 + 3 = 5
    expected_idx = 1 + ClockingSheet.DATA_ROW_INIT
    mapper_mock.clocking_to_sheet.return_value = clocking_sheet
    # When
    adapter.upsert_clocking(clocking)
    # Then
    adapter.spreadsheet.values_update.assert_called_with(
        range=f"{ClockingSheet.SHEET}!{ClockingSheet.DATA_COL_INIT}{expected_idx}:{ClockingSheet.DATA_COL_END}{expected_idx}",
        params=adapter.DEFAULT_PARAMS, body={"values": [clocking_sheet.to_row_values()]})
    adapter.circuit_breaker.call.assert_called()


@patch('pururu.infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
def test_upsert_clocking_game_id_not_found(mapper_mock, clocking: Clocking, clocking_sheet: ClockingSheet):
    # Given
    adapter = set_up()
    adapter.spreadsheet.values_get.return_value = {
        'values': [
            [clocking.game_id - 1], # Actual idx = idx + starting row = 0 + 3 = 3
            [clocking.game_id+1], # Actual idx = idx + starting row = 1 + 3 = 4
            [clocking.game_id + 2]]} # Actual idx = idx + starting row = 2 + 3 = 5
    expected_idx = 6 # new row
    mapper_mock.clocking_to_sheet.return_value = clocking_sheet
    # When
    adapter.upsert_clocking(clocking)
    # Then
    adapter.spreadsheet.values_update.assert_called_with(
        range=f"{ClockingSheet.SHEET}!{ClockingSheet.DATA_COL_INIT}{expected_idx}:{ClockingSheet.DATA_COL_END}{expected_idx}",
        params=adapter.DEFAULT_PARAMS, body={"values": [clocking_sheet.to_row_values()]})
    adapter.circuit_breaker.call.assert_called()


@patch('pururu.infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
def test_cache_ok(mapper_mock, attendance: Attendance, attendance_sheet: AttendanceSheet):
    # Given
    adapter = set_up()
    adapter.cache[f'{AttendanceSheet.SHEET}_last_row'] = 2
    adapter.spreadsheet.values_get.return_value = {'values': [[], [], []]}
    mapper_mock.gs_to_attendance_sheet.return_value = attendance_sheet
    mapper_mock.sheet_to_attendance.return_value = attendance
    # When
    adapter.get_last_attendance()
    # Then
    assert_that(adapter.cache[f'{AttendanceSheet.SHEET}_last_row'], equal_to(4))


@patch('pururu.infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
@pytest.mark.usefixtures("attendance", "attendance_sheet")
def test_get_last_attendance_ok(mapper_mock, attendance: Attendance, attendance_sheet: AttendanceSheet):
    # Given
    adapter = set_up()
    adapter.spreadsheet.values_get.side_effect = [{'values': []}, {'values': [attendance_sheet.to_row_values()]}]
    mapper_mock.gs_to_attendance_sheet.return_value = attendance_sheet
    mapper_mock.sheet_to_attendance.return_value = attendance
    # When
    result = adapter.get_last_attendance()
    # Then
    assert_that(result, equal_to(attendance))
    adapter.circuit_breaker.force_check.assert_called()


@patch('pururu.infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
def test_get_all_attendances_ok(mapper_mock, attendance_sheet: AttendanceSheet):
    # Given
    adapter = set_up()
    adapter.spreadsheet.values_get.return_value = {
        'values': [attendance_sheet.to_row_values(), attendance_sheet.to_row_values()]}
    mapper_mock.gs_to_attendance_sheet.return_value = attendance_sheet
    # When
    result = adapter.get_all_attendances()
    # Then
    assert_that(result, has_length(2))
    assert_that(mapper_mock.gs_to_attendance_sheet.call_count, equal_to(2))
    assert_that(result[0].game_id, 4)
    assert_that(result[1].game_id, 5)
    adapter.spreadsheet.values_get.assert_called_with(
        f"{AttendanceSheet.SHEET}!{AttendanceSheet.DATA_COL_INIT}{AttendanceSheet.DATA_ROW_INIT}"
        f":{AttendanceSheet.DATA_COL_END}2")
    adapter.circuit_breaker.force_check.assert_called()


def test_get_player_coins_ok():
    # Given
    adapter = set_up()
    player: str = 'member1'
    adapter.spreadsheet.values_get.return_value = {
        'values': [['member1', 'member2'], [10, 20]]}
    # When
    result = adapter.get_player_coins(player)
    # Then
    assert_that(result, equal_to(10))
    adapter.spreadsheet.values_get.assert_called_with(
        f"{CoinsSheet.SHEET}!{CoinsSheet.DATA_COL_INIT}{CoinsSheet.DATA_ROW_INIT}"
        f":{CoinsSheet.DATA_COL_END}{CoinsSheet.DATA_ROW_END}")
    adapter.circuit_breaker.force_check.assert_called()

def test_fallback_in_memory_data_add():
    # Given
    adapter = set_up()
    func = Mock(side_effect=lambda x, y: x+y)
    # When
    adapter.in_memory_fallback.add(func, 1, 2)
    # Then
    assert_that(adapter.in_memory_fallback.data, equal_to([{"function": func, "args":(1,2), "kwargs":{}}]))

def test_fallback_in_memory_data_get_and_clear():
    # Given
    adapter = set_up()
    func = Mock(side_effect=lambda x, y: x+y)
    adapter.in_memory_fallback.data = [{"function": func, "args":(1,2), "kwargs":{}}, {"function": func, "args":(3,4), "kwargs":{}}, {"function": func, "args":(5,6), "kwargs":{}}]
    # When
    for idx, item in enumerate(adapter.in_memory_fallback.get_and_clear()):
        item["function"](*item["args"], **item["kwargs"])
    # Then
    assert_that(adapter.in_memory_fallback.data, equal_to([]))

def test_use_fallback_ok():
    # Given
    adapter = set_up()
    func = Mock(side_effect=lambda x, y: x+y)
    # When
    adapter._use_fallback(func,1, 2)
    # Then
    assert_that(adapter.in_memory_fallback.data, equal_to([{"function": func, "args":(1,2), "kwargs":{}}]))

def test_fallback_recovery_ok():
    # Given
    adapter = set_up()
    func = Mock(side_effect=lambda x, y: x+y)
    error_func = Mock(side_effect=Exception("Error"))
    adapter.in_memory_fallback.data = [{"function": func, "args": (1, 2), "kwargs": {}},
                                       {"function": error_func, "args": (3, 4), "kwargs": {}},
                                       {"function": func, "args": (5, 6), "kwargs": {}}]
    # When
    with pytest.raises(Exception):
        adapter._fallback_recovery()
    # Then
    assert_that(adapter.in_memory_fallback.data, equal_to([{"function": error_func, "args": (3, 4), "kwargs": {}},
                                       {"function": func, "args": (5, 6), "kwargs": {}}]))
    assert_that(func.call_count, equal_to(1))
    assert_that(error_func.call_count, equal_to(1))