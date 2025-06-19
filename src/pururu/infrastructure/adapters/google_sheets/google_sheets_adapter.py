import warnings

import gspread
from google.oauth2.service_account import Credentials

import pururu.config as config
import pururu.infrastructure.adapters.google_sheets.mapper as mapper
from pururu.common import logger
from pururu.common.circuit_breaker import CircuitBreaker
from pururu.domain.entities import BotEvent, Attendance, Clocking
from pururu.domain.services.database_service import DatabaseInterface
from pururu.infrastructure.adapters.google_sheets.entities import AttendanceSheet, BotEventSheet, ClockingSheet, \
    CoinsSheet


class FallBackInMemoryStorage:
    def __init__(self):
        self.data = []

    def add(self, function, *args, **kwargs):
        return self.data.append({"function": function, "args": args, "kwargs": kwargs})

    def return_item(self, item):
        self.data.insert(0, item)

    def get_and_clear(self):
        while self.data:
            yield self.data.pop(0)


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
        self.logger = logger.get_logger(__name__)
        self.cache = {}
        self.in_memory_fallback = FallBackInMemoryStorage()
        self.circuit_breaker = CircuitBreaker(failure_threshold=config.GS_FAILURE_THRESHOLD,
                                              recovery_timeout=config.GS_RECOVERY_TIMEOUT,
                                              open_fallback=self._use_fallback, on_half_open=self._fallback_recovery)

    def upsert_attendance(self, attendance: Attendance) -> None:
        """
        Upsert an attendance row into the Google sheet
        :param attendance: Attendance; the attendance to be upserted
        :return: None
        """
        self.circuit_breaker.call(self._upsert_attendance, attendance)

    def _upsert_attendance(self, attendance: Attendance) -> None:
        try:
            self.logger.debug("Upserting attendance", extra={"game_id": attendance.game_id})
            sheet = mapper.attendance_to_sheet(attendance)

            self.spreadsheet.values_update(
                range=self.__build_data_notation(AttendanceSheet.SHEET, AttendanceSheet.DATA_COL_INIT, sheet.game_id,
                                                 AttendanceSheet.DATA_COL_END, sheet.game_id),
                params=self.DEFAULT_PARAMS, body={"values": [sheet.to_row_values()]})
        except Exception:
            self.logger.error("Error upserting attendance", exc_info=True,
                              extra={"game_id": attendance.game_id, "attendance_data": attendance.__dict__})
            raise

    def get_all_attendances(self) -> list[Attendance]:
        """
        Get all attendances from the Google sheet
        :return: list[Attendance]; all attendances
        """
        try:
            self.logger.debug("Querying all attendances")
            self.circuit_breaker.force_check()
            all_attendances = []
            last_row = self.__get_last_row(AttendanceSheet.SHEET)
            attendance_value_range = self.spreadsheet.values_get(
                self.__build_data_notation(AttendanceSheet.SHEET, AttendanceSheet.DATA_COL_INIT,
                                           AttendanceSheet.DATA_ROW_INIT,
                                           AttendanceSheet.DATA_COL_END, last_row))
            for idx, row in enumerate(attendance_value_range['values']):
                attendance_id = idx + AttendanceSheet.DATA_ROW_INIT
                attendance = mapper.gs_to_attendance_sheet(attendance_id, row)
                all_attendances.append(mapper.sheet_to_attendance(attendance))
            self.logger.debug(f"Fetched a total of {len(all_attendances)} attendances", extra={"last_row": last_row})
            return all_attendances
        except Exception as e:
            self.logger.error("Error getting all attendances", exc_info=True)
            raise

    def get_player_coins(self, player) -> int:
        """
        Get the coins of a player from the Google sheet
        :param player: player name
        :return: int: coins of the player
        """
        try:
            self.logger.debug("Querying player coins", extra={"player": player})
            self.circuit_breaker.force_check()

            attendance_value_range = self.spreadsheet.values_get(
                self.__build_data_notation(CoinsSheet.SHEET, CoinsSheet.DATA_COL_INIT,
                                           CoinsSheet.DATA_ROW_INIT,
                                           CoinsSheet.DATA_COL_END, CoinsSheet.DATA_ROW_END))

            column = attendance_value_range['values'][0].index(player)
            player_coins = attendance_value_range['values'][1][column]
            self.logger.debug(f"Total coins for player {player}: {player_coins}", extra={"player": player})
            return player_coins
        except Exception as e:
            self.logger.error("Error getting player coins", exc_info=True, extra={"player": player})
            raise

    def upsert_clocking(self, clocking: Clocking) -> None:
        """
        Upsert a clocking row into the Google sheet
        :param clocking: The clocking to be upserted
        :return: None
        """
        self.circuit_breaker.call(self._upsert_clocking, clocking)

    def _upsert_clocking(self, clocking: Clocking) -> None:
        try:
            self.logger.debug(f"Upserting clocking", extra={"game_id": clocking.game_id})
            game_id_rows = self.spreadsheet.values_get(
                self.__build_data_notation(sheet=ClockingSheet.SHEET, col_start=ClockingSheet.DATA_COL_INIT,
                                           row_start=ClockingSheet.DATA_ROW_INIT, col_end=ClockingSheet.DATA_COL_INIT))
            game_ids = [int(row[0]) for row in game_id_rows['values']]
            row_idx = ClockingSheet.DATA_ROW_INIT
            row_idx = row_idx + (game_ids.index(clocking.game_id) if clocking.game_id in game_ids else len(game_ids))
            sheet = mapper.clocking_to_sheet(clocking)
            self.spreadsheet.values_update(
                range=self.__build_data_notation(ClockingSheet.SHEET, ClockingSheet.DATA_COL_INIT, row_idx,
                                                 ClockingSheet.DATA_COL_END, row_idx),
                params=self.DEFAULT_PARAMS, body={"values": [sheet.to_row_values()]})
        except Exception as e:
            self.logger.error("Error upserting clocking", exc_info=True,
                              extra={"game_id": clocking.game_id, "clocking_data": clocking.__dict__})
            raise

    def insert_bot_event(self, bot_event: BotEvent) -> None:
        """
        DEPRECATED
        Register a bot event in the Google sheet
        :param bot_event: the event
        :return: None
        """
        warnings.warn("insert_bot_event is deprecated", DeprecationWarning)
        self.logger.warning("DEPRECATED: insert_bot_event is deprecated and should not be used")
        self.circuit_breaker.call(self._insert_bot_event, bot_event)

    def _insert_bot_event(self, bot_event: BotEvent) -> None:
        sheet = mapper.bot_event_to_sheet(bot_event)
        row_idx = self.__get_last_row(BotEventSheet.SHEET) + 1
        self.spreadsheet.values_update(
            range=self.__build_data_notation(BotEventSheet.SHEET, BotEventSheet.DATA_COL_INIT, row_idx),
            params=self.DEFAULT_PARAMS, body={"values": [sheet.to_row_values()]})

    def get_last_attendance(self) -> Attendance:
        """
        Get the last attendance from the Google sheet
        :return: Attendance; last attendance row
        """
        try:
            self.logger.debug("Getting last attendance")
            self.circuit_breaker.force_check()
            attendance_idx = self.__get_last_row(AttendanceSheet.SHEET)
            attendance_value_range = self.spreadsheet.values_get(
                self.__build_data_notation(AttendanceSheet.SHEET, AttendanceSheet.DATA_COL_INIT, attendance_idx,
                                           AttendanceSheet.DATA_COL_END, attendance_idx))
            attendance_row = attendance_value_range['values'][0]
            attendance = mapper.gs_to_attendance_sheet(game_id=attendance_idx, row=attendance_row)
            self.logger.debug("Last attendance fetched!",
                              extra={"row_idx": attendance_row, "game_id": attendance.game_id})
            return mapper.sheet_to_attendance(attendance)
        except:
            self.logger.error("Error getting last attendance", exc_info=True)
            raise

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

    def _use_fallback(self, function, *args, **kwargs):
        self.logger.warning(
            "Using fallback due to circuit breaker open state"
        )
        self.in_memory_fallback.add(function, *args, **kwargs)

    def _fallback_recovery(self):
        self.logger.info("Recovering from fallback")
        for fallback_item in self.in_memory_fallback.get_and_clear():
            try:
                fallback_item["function"](*fallback_item["args"], **fallback_item["kwargs"])
            except Exception as e:
                self.in_memory_fallback.return_item(fallback_item)
                self.logger.error(
                    "Fallback retry failed",
                    exc_info=True,
                    extra={"function": fallback_item["function"].__name__}
                )
                raise
