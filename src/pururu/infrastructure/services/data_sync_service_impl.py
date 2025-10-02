from pururu.common import logger
from pururu.domain.entities.session import Session
from pururu.domain.services.data_sync_service import DataSyncService
from pururu.infrastructure.adapters.google_sheets.google_sheets_adapter import GoogleSheetsAdapter
from pururu.infrastructure.adapters.google_sheets.mapper import GoogleSheetsMapper


class DataSyncServiceImpl(DataSyncService):
    def __init__(self, google_sheets_adapter: GoogleSheetsAdapter):
        self.google_sheets_adapter = google_sheets_adapter
        self.logger = logger.get_logger(__name__)

    def sync_session(self, session: Session) -> None:
        """
        Syncs a session to Google Sheets
        :param session: session to sync
        :return: None
        """
        try:
            self.logger.debug(f"Syncing session id {session.id} to Google Sheets",
                              extra={"session_id": session.id})
            attendance = GoogleSheetsMapper.to_attendance(session)
            game_id = self.google_sheets_adapter.upsert_attendance(attendance)
            self.logger.debug(f"Attendance {game_id} created in Google Sheets; syncing clock data")
            clocking = GoogleSheetsMapper.to_clocking(session, game_id)
            self.google_sheets_adapter.upsert_clocking(clocking)
            self.logger.debug(f"Session id {session.id} synced to Google Sheets",
                              extra={"session_id": session.id})
        except Exception as e:
            self.logger.error("Failed to sync session to Google Sheets", exc_info=True, extra={
                "session_id": session.id
            })
            raise e
