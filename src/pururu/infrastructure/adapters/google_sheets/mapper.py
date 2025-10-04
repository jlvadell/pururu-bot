from pururu.config import settings
from pururu.domain.entities.session import Session, Type
from pururu.infrastructure.adapters.google_sheets.entities import AttendanceSheet, ClockingSheet


class GoogleSheetsMapper:
    TYPE_MAP = {
        'Juegueo Oficial': Type.OFFICIAL_GAME,
        'Juegueo Adicional Oficial': Type.ADDITIONAL_GAME,
        'Quedada Oficial': Type.OFFICIAL_MEETING
    }
    REVERSE_TYPE_MAP = {v: k for k, v in TYPE_MAP.items()}

    @staticmethod
    def to_attendance(session: Session) -> AttendanceSheet:
        # sorting is needed to match the order in the Google Sheet
        sorted_player_sessions = sorted(session.players,
                                        key=lambda player_session: settings.google_sheets.general.player_order.get(
                                            player_session.player_id, float('inf')))
        player_attendance = [player_session.attended for
                             player_session in sorted_player_sessions]

        return AttendanceSheet(
            session.id,
            None,
            [GoogleSheetsMapper._parse_bool_to_str(not
                                                   attended) for
             attended in player_attendance],
            [GoogleSheetsMapper._parse_bool_to_str(not attended and not player_session.justified_absence) for
             (attended, player_session) in zip(player_attendance, sorted_player_sessions)],
            [player_session.motive for player_session in sorted_player_sessions],
            session.get_official_start_time().isoformat(sep=" ",
                                                        timespec="seconds") if session.get_official_start_time() is not None else "",
            GoogleSheetsMapper._parse_type_to_str(session.type)
        )

    @staticmethod
    def to_clocking(session: Session, game_id: int) -> ClockingSheet:
        # sorting is needed to match the order in the Google Sheet
        sorted_player_sessions = sorted(session.players,
                                        key=lambda player_session: settings.google_sheets.general.player_order.get(
                                            player_session.player_id, float('inf')))
        return ClockingSheet(
            game_id,
            [player_session.get_total_time(
                crop_initial=session.get_official_start_time(settings.general.min_attendance_members),
                crop_final=session.get_official_end_time(settings.general.min_attendance_members))
                for player_session in sorted_player_sessions]
        )

    @staticmethod
    def _parse_bool_to_str(value: bool) -> str:
        return 'TRUE' if value else 'FALSE'

    @staticmethod
    def _parse_type_from_str(value: str) -> Type:
        return GoogleSheetsMapper.TYPE_MAP.get(value, Type.OFFICIAL_GAME)

    @staticmethod
    def _parse_type_to_str(value: Type) -> str:
        return GoogleSheetsMapper.REVERSE_TYPE_MAP.get(value, 'Juegueo Oficial')
