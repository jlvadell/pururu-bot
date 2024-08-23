import gspread
from google.oauth2.service_account import Credentials

import pururu.infrastructure.adapters.google_sheets.mapper as mapper
import pururu.utils as utils
from pururu.domain.entities import BotEvent, Attendance, Clocking
from pururu.domain.services.database_service import DatabaseInterface
from pururu.infrastructure.adapters.google_sheets.entities import AttendanceSheet, BotEventSheet, ClockingSheet


class GoogleSheetsAdapter(DatabaseInterface):
    """
    DatabaseInterface Implementation for using Google Sheets as DB, check the docs:
    https://developers.google.com/sheets/api/guides/values#python
    """

    DEFAULT_PARAMS = {"valueInputOption": "USER_ENTERED"}

    def __init__(self, credentials_path: str, spreadsheet_id: str):
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive',
                  'https://www.googleapis.com/auth/drive.file']
        self.credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        self.client = gspread.authorize(self.credentials)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        self.logger = utils.get_logger(__name__)
        self.cache = {}

    def upsert_attendance(self, attendance: Attendance) -> None:
        sheet = mapper.attendance_to_sheet(attendance)
        self.spreadsheet.values_update(
            range=self.__build_data_notation(AttendanceSheet.SHEET, AttendanceSheet.DATA_COL_INIT, sheet.game_id,
                                             AttendanceSheet.DATA_COL_END, sheet.game_id),
            params=self.DEFAULT_PARAMS, body={"values": [sheet.to_row_values()]})

    def insert_clocking(self, clocking: Clocking) -> None:
        sheet = mapper.clocking_to_sheet(clocking)
        row_idx = self.__get_last_row(ClockingSheet.SHEET) + 1
        self.spreadsheet.values_update(
            range=self.__build_data_notation(ClockingSheet.SHEET, ClockingSheet.DATA_COL_INIT, row_idx,
                                             ClockingSheet.DATA_COL_END, row_idx),
            params=self.DEFAULT_PARAMS, body={"values": [sheet.to_row_values()]})

    def insert_bot_event(self, bot_event: BotEvent) -> None:
        """
        Register a bot event in the Google sheet
        :param bot_event: the event
        :return: None
        """
        sheet = mapper.bot_event_to_sheet(bot_event)
        row_idx = self.__get_last_row(BotEventSheet.SHEET) + 1
        self.spreadsheet.values_update(
            range=self.__build_data_notation(BotEventSheet.SHEET, BotEventSheet.DATA_COL_INIT, row_idx),
            params=self.DEFAULT_PARAMS, body={"values": [sheet.to_row_values()]})

    def get_last_attendance(self) -> Attendance:
        self.logger.debug("Getting last attendance")
        attendance_idx = self.__get_last_row(AttendanceSheet.SHEET)
        attendance_value_range = self.spreadsheet.values_get(
            self.__build_data_notation(AttendanceSheet.SHEET, AttendanceSheet.DATA_COL_INIT, attendance_idx,
                                       AttendanceSheet.DATA_COL_END, attendance_idx))
        self.logger.debug(f"find last attendance result: {attendance_value_range}")
        attendance_row = attendance_value_range['values'][0]
        attendance = mapper.gs_to_attendance_sheet(game_id=attendance_idx, row=attendance_row)
        self.logger.debug(f"Attendance sheet: {attendance}")
        return mapper.sheet_to_attendance(attendance)

    def __get_last_row(self, sheet: str, col: str = "A") -> int:
        """
        Given a sheet with n rows with data in column 'col', return the max index of the last row with data
        :param sheet: the sheet name (check entities.SHEET values)
        :param col: the columns where the data is stored; defaults to 'C'
        :return: the index of the last row with data
        """
        current_max = 1
        if f'{sheet}_last_row' in self.cache:
            current_max = self.cache[f'{sheet}_last_row']

        rows = self.spreadsheet.values_get(self.__build_data_notation(sheet, col, current_max, col))
        actual_max = current_max + len(rows['values']) - 1
        self.cache[f'{sheet}_last_row'] = actual_max
        return actual_max

    @staticmethod
    def __build_data_notation(sheet: str, col_start: str, row_start: int = None, col_end: str = None,
                              row_end: int = None) -> str:
        """
        Given google sheet, row, column or range data, return the correct A1 for the google sheets API.
        Check out google_docs: https://developers.google.com/sheets/api/guides/concepts#expandable-1
        :param sheet: the sheet name (check entities.SHEET values)
        :param col_start: the column where the data starts, e.g. 'A' (check entities.DATA_COL_INIT)
        :param row_start: the row index where the data starts
        :param col_end: the column where the data ends, e.g. 'A' (check entities.DATA_COL_END)
        :param row_end: the row index where the data ends
        :return: the correct A1 notation for the google sheets API, e.g. 'Sheet1!A1:B2' or 'Sheet1!A:A' or 'Sheet1!A1'
        """
        if row_start and col_end and row_end:
            return f'{sheet}!{col_start}{row_start}:{col_end}{row_end}'
        elif row_start and col_end:
            return f'{sheet}!{col_start}{row_start}:{col_end}'
        elif row_start:
            return f'{sheet}!{col_start}{row_start}'
        return f'{sheet}!{col_start}:{col_start}'
