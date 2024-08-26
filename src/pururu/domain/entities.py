from enum import Enum


class BotEvent:
    def __init__(self, event_type: str, date: str, description: str):
        self.event_type = event_type
        self.date = date
        self.description = description


class MemberAttendance:
    def __init__(self, member: str, attendance: bool, justified: bool, motive: str):
        self.member = member
        self.attendance = attendance
        self.justified = justified
        self.motive = motive


class AttendanceEventType(Enum):
    OFFICIAL_GAME = "Juegueo Oficial"
    ADDITIONAL_OFFICIAL_GAME = "Juegueo Adicional Oficial"
    OFFICIAL_MEETING = "Quedada Oficial"
    UNKNOWN = "unknown"

    @staticmethod
    def of(description: str) -> 'AttendanceEventType':
        for event_type in AttendanceEventType:
            if event_type.value == description:
                return event_type
        return AttendanceEventType.UNKNOWN


class Attendance:
    def __init__(self, game_id: int, members: list[MemberAttendance], date: str, event_type: AttendanceEventType):
        self.game_id = game_id
        self.members = members
        self.date = date
        self.event_type = event_type


class Clocking:
    def __init__(self, game_id: int, playtimes: list[int]):
        self.game_id = game_id
        self.playtimes = playtimes
