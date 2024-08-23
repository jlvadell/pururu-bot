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

    def __init__(self, game_id: int, absence: list, unjustified: list, motives: list, date: str,
                 description: str):
        self.game_id = game_id
        self.absence = absence
        self.unjustified = unjustified
        self.motives = motives
        self.date = date
        self.description = description

    def to_row_values(self):
        row = [self.description, self.date]
        for i in range(len(self.absence)):
            row.append(self.absence[i])
            row.append(self.unjustified[i])
            row.append(self.motives[i] if i < len(self.motives) else "")
        return row


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
