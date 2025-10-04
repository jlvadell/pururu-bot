import gspread
from google.oauth2.service_account import Credentials

from pururu.common import logger
from pururu.infrastructure.adapters.google_sheets.entities import AttendanceSheet, ClockingSheet


class GoogleSheetsAdapter:
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
        self.logger = logger.get_logger(__name__)

    def upsert_attendance(self, attendance: AttendanceSheet) -> int:
        """
        Upsert an attendance row into the Google sheet
        :param attendance: Attendance; the attendance to be upserted
        :return: int; the game_id of the inserted attendance
        """
        try:
            session_id_rows = self.spreadsheet.values_get(
                self._build_data_notation(sheet=AttendanceSheet.SHEET, col_start=AttendanceSheet.DATA_COL_INIT,
                                          row_start=AttendanceSheet.DATA_ROW_INIT,
                                          col_end=AttendanceSheet.DATA_COL_INIT))
            session_ids = [str(row[0]) for row in session_id_rows['values']]
            row_idx = AttendanceSheet.DATA_ROW_INIT
            row_idx = row_idx + (
                session_ids.index(attendance.session_id) if attendance.session_id in session_ids else len(session_ids))
            attendance.game_id = row_idx
            self.logger.debug(f"Upserting attendance for game_id {attendance.game_id}",
                              extra={"game_id": attendance.game_id})

            self.spreadsheet.values_update(
                range=self._build_data_notation(AttendanceSheet.SHEET, AttendanceSheet.DATA_COL_INIT,
                                                attendance.game_id,
                                                AttendanceSheet.DATA_COL_END, attendance.game_id),
                params=self.DEFAULT_PARAMS, body={"values": [attendance.to_row_values()]})
            return attendance.game_id
        except Exception:
            self.logger.error(f"Error upserting attendance for game_id {attendance.game_id}", exc_info=True,
                              extra={"game_id": attendance.game_id, "attendance_data": attendance.__dict__})
            raise

    def upsert_clocking(self, clocking: ClockingSheet) -> None:
        """
        Upsert a clocking row into the Google sheet
        :param clocking: The clocking to be upserted
        :return: None
        """
        try:
            self.logger.debug(f"Upserting clocking for game_id {clocking.game_id}", extra={"game_id": clocking.game_id})
            game_id_rows = self.spreadsheet.values_get(
                self._build_data_notation(sheet=ClockingSheet.SHEET, col_start=ClockingSheet.DATA_COL_INIT,
                                          row_start=ClockingSheet.DATA_ROW_INIT, col_end=ClockingSheet.DATA_COL_INIT))
            game_ids = [int(row[0]) for row in game_id_rows['values']]
            row_idx = ClockingSheet.DATA_ROW_INIT
            row_idx = row_idx + (game_ids.index(clocking.game_id) if clocking.game_id in game_ids else len(game_ids))
            self.spreadsheet.values_update(
                range=self._build_data_notation(ClockingSheet.SHEET, ClockingSheet.DATA_COL_INIT, row_idx,
                                                ClockingSheet.DATA_COL_END, row_idx),
                params=self.DEFAULT_PARAMS, body={"values": [clocking.to_row_values()]})
        except Exception:
            self.logger.error(f"Error upserting clocking for game_id {clocking.game_id}", exc_info=True,
                              extra={"game_id": clocking.game_id, "clocking_data": clocking.__dict__})
            raise

    @staticmethod
    def _build_data_notation(sheet: str, col_start: str, row_start: int = None, col_end: str = None,
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
