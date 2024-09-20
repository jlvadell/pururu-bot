import pytest
from hamcrest import assert_that, has_length, equal_to

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
@patch('pururu.utils.get_logger')
def set_up(gspread_mock, credentials_mock, logger_mock) -> GoogleSheetsAdapter:
    gs_client_mock = Mock()
    gspread_mock.authorize.return_value = gs_client_mock
    gs_client_mock.open_by_key.return_value = gs_client_mock
    return GoogleSheetsAdapter('credentials.json', 'spreadsheet_id')


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


@patch('pururu.infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
def test_cache_ok(mapper_mock, bot_event: BotEvent, bot_event_sheet: BotEventSheet):
    # Given
    adapter = set_up()
    adapter.cache[f'{BotEventSheet.SHEET}_last_row'] = 2
    adapter.spreadsheet.values_get.return_value = {'values': [[], [], []]}
    mapper_mock.bot_event_to_sheet.return_value = bot_event_sheet
    # When
    adapter.insert_bot_event(bot_event)
    # Then
    adapter.spreadsheet.values_get.assert_called_with(
        f"{BotEventSheet.SHEET}!{BotEventSheet.DATA_COL_INIT}2:{BotEventSheet.DATA_COL_INIT}", )
    assert_that(adapter.cache[f'{BotEventSheet.SHEET}_last_row'], equal_to(4))


@patch('pururu.infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
@pytest.mark.usefixtures("bot_event", "bot_event_sheet")
def test_insert_bot_event_ok(mapper_mock, bot_event: BotEvent, bot_event_sheet: BotEventSheet):
    # Given
    adapter = set_up()
    mapper_mock.bot_event_to_sheet.return_value = bot_event_sheet
    adapter.spreadsheet.values_get.return_value = {'values': []}
    # When
    adapter.insert_bot_event(bot_event)
    # Then
    adapter.spreadsheet.values_update.assert_called_with(
        range=f"{BotEventSheet.SHEET}!{BotEventSheet.DATA_COL_INIT}1",
        params=adapter.DEFAULT_PARAMS, body={"values": [bot_event_sheet.to_row_values()]})


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
    adapter.spreadsheet.values_get.assert_called_with(
        f"{AttendanceSheet.SHEET}!{AttendanceSheet.DATA_COL_INIT}{AttendanceSheet.DATA_ROW_INIT}"
        f":{AttendanceSheet.DATA_COL_END}2")


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
