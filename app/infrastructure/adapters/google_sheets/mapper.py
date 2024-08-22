import config
from domain.entities import Attendance, BotEvent, MemberAttendance, Clocking
from infrastructure.adapters.google_sheets.entities import AttendanceSheet, BotEventSheet, ClockingSheet


def bot_event_to_sheet(domain_entity: BotEvent) -> BotEventSheet:
    return BotEventSheet(domain_entity.event_type, domain_entity.date, domain_entity.description)


def attendance_to_sheet(domain_entity: Attendance) -> AttendanceSheet:
    attendance = []
    justified = []
    motives = []
    for member in domain_entity.members:
        attendance.append(__parse_bool_to_str(member.attendance))
        justified.append(__parse_bool_to_str(member.justified))
        motives.append(member.motive)
    return AttendanceSheet(domain_entity.game_id, attendance, justified, motives, domain_entity.date,
                           domain_entity.description)


def clocking_to_sheet(domain_entity: Clocking) -> ClockingSheet:
    return ClockingSheet(domain_entity.member, str(domain_entity.game_id), domain_entity.clock_in,
                         domain_entity.clock_out)


def sheet_to_attendance(sheet: AttendanceSheet) -> Attendance:
    members = []
    for idx, player in enumerate(config.GS_ATTENDANCE_PLAYER_MAPPING.keys()):
        members.append(MemberAttendance(player, __parse_str_to_bool(sheet.absence[idx]),
                                        __parse_str_to_bool(sheet.unjustified[idx]), sheet.motives[idx]))

    return Attendance(sheet.game_id, members, sheet.date, sheet.description)


def gs_to_attendance_sheet(game_id: int, row: list) -> AttendanceSheet:
    absence = []
    unjustified = []
    motives = []
    for cell in config.GS_ATTENDANCE_PLAYER_MAPPING.values():
        idx = __column_to_index(cell)
        absence.append(row[idx])
        unjustified.append(row[idx + 1])
        if idx + 2 < len(row):
            motives.append(row[idx + 2])
        else:
            motives.append('')

    return AttendanceSheet(game_id, absence, unjustified, motives, row[1], row[0])


def __parse_str_to_bool(value: str) -> bool:
    return False if value == 'TRUE' else True


def __parse_bool_to_str(value: bool) -> str:
    if value:
        return 'FALSE'
    return 'TRUE'


def __column_to_index(col: str) -> int:
    return ord(col.upper()) - 65


def __index_to_column(idx: int) -> str:
    return chr(idx + 65)
