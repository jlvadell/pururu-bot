import pytest

from domain.entities import Attendance, Clocking, BotEvent
from infrastructure.adapters.google_sheets.entities import AttendanceSheet, ClockingSheet, BotEventSheet
from test_domain.test_entities import attendance, clocking, bot_event
from test_infrastructure.test_adapters.test_google_sheets.test_entities import attendance_sheet, clocking_sheet, \
    bot_event_sheet
from infrastructure.adapters.google_sheets.google_sheets_adapter import GoogleSheetsAdapter

from unittest.mock import patch, Mock


@patch('infrastructure.adapters.google_sheets.google_sheets_adapter.gspread')
@patch('google.oauth2.service_account.Credentials.from_service_account_file')
@patch('utils.get_logger')
def set_up(gspread_mock, credentials_mock, logger_mock) -> GoogleSheetsAdapter:
    gs_client_mock = Mock()
    gspread_mock.authorize.return_value = gs_client_mock
    gs_client_mock.open_by_key.return_value = gs_client_mock
    return GoogleSheetsAdapter('credentials.json', 'spreadsheet_id')


@patch('infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
@pytest.mark.usefixtures("attendance", "attendance_sheet")
def test_upsert_attendance_ok(mapper_mock, attendance: Attendance, attendance_sheet: AttendanceSheet):
    adapter = set_up()
    mapper_mock.attendance_to_sheet.return_value = attendance_sheet
    adapter.upsert_attendance(attendance)
    adapter.spreadsheet.values_update.assert_called_with(
        range=f"{AttendanceSheet.SHEET}!{AttendanceSheet.DATA_COL_INIT}{attendance_sheet.game_id}:"
              f"{AttendanceSheet.DATA_COL_END}{attendance_sheet.game_id}",
        params=adapter.DEFAULT_PARAMS, body={"values": [attendance_sheet.to_row_values()]}
    )


@patch('infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
@pytest.mark.usefixtures("clocking", "clocking_sheet")
def test_insert_clocking_ok(mapper_mock, clocking: Clocking, clocking_sheet: ClockingSheet):
    adapter = set_up()
    mapper_mock.clocking_to_sheet.return_value = clocking_sheet
    adapter.spreadsheet.values_get.return_value = {'values': []}
    adapter.insert_clocking(clocking)
    adapter.spreadsheet.values_update.assert_called_with(
        range=f"{ClockingSheet.SHEET}!{ClockingSheet.DATA_COL_INIT}1:{ClockingSheet.DATA_COL_END}1",
        params=adapter.DEFAULT_PARAMS, body={"values": [clocking_sheet.to_row_values()]})


@patch('infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
@pytest.mark.usefixtures("clocking", "clocking_sheet")
def test_cache_ok(mapper_mock, clocking: Clocking, clocking_sheet: ClockingSheet):
    adapter = set_up()
    adapter.cache[f'{ClockingSheet.SHEET}_last_row'] = 2
    adapter.spreadsheet.values_get.return_value = {'values': [[], [], []]}
    mapper_mock.clocking_to_sheet.return_value = clocking_sheet
    adapter.insert_clocking(clocking)
    adapter.spreadsheet.values_get.assert_called_with(
        f"{ClockingSheet.SHEET}!{ClockingSheet.DATA_COL_INIT}2:{ClockingSheet.DATA_COL_INIT}", )
    assert adapter.cache[f'{ClockingSheet.SHEET}_last_row'] == 4


@patch('infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
@pytest.mark.usefixtures("bot_event", "bot_event_sheet")
def test_insert_bot_event_ok(mapper_mock, bot_event: BotEvent, bot_event_sheet: BotEventSheet):
    adapter = set_up()
    mapper_mock.bot_event_to_sheet.return_value = bot_event_sheet
    adapter.spreadsheet.values_get.return_value = {'values': []}
    adapter.insert_bot_event(bot_event)
    adapter.spreadsheet.values_update.assert_called_with(
        range=f"{BotEventSheet.SHEET}!{BotEventSheet.DATA_COL_INIT}1",
        params=adapter.DEFAULT_PARAMS, body={"values": [bot_event_sheet.to_row_values()]})


@patch('infrastructure.adapters.google_sheets.google_sheets_adapter.mapper')
@pytest.mark.usefixtures("attendance", "attendance_sheet")
def test_get_last_attendance_ok(mapper_mock, attendance: Attendance, attendance_sheet: AttendanceSheet):
    adapter = set_up()
    adapter.spreadsheet.values_get.side_effect = [{'values': []}, {'values': [attendance_sheet.to_row_values()]}]
    mapper_mock.gs_to_attendance_sheet.return_value = attendance_sheet
    mapper_mock.sheet_to_attendance.return_value = attendance
    result = adapter.get_last_attendance()
    assert result == attendance
