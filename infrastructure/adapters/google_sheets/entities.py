class BotEventSheet:
    SHEET = "Eventos"
    DATA_COL_INIT = "A"
    DATA_COL_END = "C"

    def __init__(self, event_type: str, date: str, description: str):
        self.event_type = event_type
        self.date = date
        self.description = description

    def to_row_values(self):
        return [self.event_type, self.date, self.description]


class AttendanceSheet:
    SHEET = "Asistencia"
    DATA_COL_INIT = "A"
    DATA_COL_END = "Q"

    def __init__(self, game_id: int, attendance: list, justified: list, motives: list, date: str,
                 description: str):
        self.game_id = game_id
        self.attendance = attendance
        self.justified = justified
        self.motives = motives
        self.date = date
        self.description = description

    def to_row_values(self):
        return [self.description, self.date, self.attendance[0], self.justified[0], self.motives[0], self.attendance[1],
                self.justified[1], self.motives[1], self.attendance[2], self.justified[2], self.motives[2],
                self.attendance[3], self.justified[3], self.motives[3], self.attendance[4], self.justified[4],
                self.motives[4]]


class ClockingSheet:
    SHEET = "Fichaje"
    DATA_COL_INIT = "A"
    DATA_COL_END = "D"

    def __init__(self, member: str, game_id: str, clock_in: str, clock_out: str):
        self.member = member
        self.game_id = game_id
        self.clock_in = clock_in
        self.clock_out = clock_out

    def to_row_values(self):
        return [self.game_id, self.member, self.clock_in, self.clock_out]
