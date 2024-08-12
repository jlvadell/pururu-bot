import config
from domain.entities import Attendance, BotEvent, MemberAttendance, Clocking
from infrastructure.adapters.google_sheets.entities import AttendanceSheet, BotEventSheet, ClockingSheet


def bot_event_to_sheet(domain_entity: BotEvent):
    return BotEventSheet(domain_entity.event_type, domain_entity.date, domain_entity.description)


def attendance_to_sheet(domain_entity: Attendance):
    attendance = []
    justified = []
    motives = []
    for member in domain_entity.members:
        attendance.append(__parse_bool_to_str(member.attendance))
        justified.append(__parse_bool_to_str(member.justified))
        motives.append(member.motive)
    return AttendanceSheet(domain_entity.game_id, attendance, justified, motives, domain_entity.date,
                           domain_entity.description)


def clocking_to_sheet(domain_entity: Clocking):
    return ClockingSheet(domain_entity.member, domain_entity.game_id, domain_entity.clock_in, domain_entity.clock_out)


def sheet_to_attendance(sheet: AttendanceSheet):
    members = []
    for idx, kero in enumerate(config.GS_ATTENDANCE_PLAYER_MAPPING.keys()):
        members.append(MemberAttendance(kero, __parse_str_to_bool(sheet.attendance[idx]),
                                        __parse_str_to_bool(sheet.justified[idx]), sheet.motives[idx]))

    return Attendance(sheet.game_id, members, sheet.date, sheet.description)


def gs_to_attendance_sheet(game_id: int, row: list):
    attendance = []
    justified = []
    motives = []
    for kero, cell in config.GS_ATTENDANCE_PLAYER_MAPPING.items():
        idx = __column_to_index(cell)
        if row[idx] == 'FALSE':
            attendance.append('TRUE')
        else:
            attendance.append('FALSE')
        if row[idx + 1] == 'TRUE':
            justified.append('FALSE')
        else:
            justified.append('TRUE')
        if idx + 2 < len(row):
            motives.append(row[idx + 2])
        else:
            motives.append('')

    return AttendanceSheet(game_id, attendance, justified, motives, row[2], row[1])


def __parse_str_to_bool(value: str):
    return value == 'TRUE'


def __parse_bool_to_str(value: bool):
    if value:
        return 'FALSE'
    return 'TRUE'


def __column_to_index(col: str):
    return ord(col.upper()) - 65


def __index_to_column(idx: int):
    return chr(idx + 65)
