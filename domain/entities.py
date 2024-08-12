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


class Attendance:
    def __init__(self, game_id: int, members: list[MemberAttendance], date: str, description: str):
        self.game_id = game_id
        self.members = members
        self.date = date
        self.description = description


class Clocking:
    def __init__(self, member: str, game_id: str, clock_in: str, clock_out: str):
        self.member = member
        self.game_id = game_id
        self.clock_in = clock_in
        self.clock_out = clock_out
