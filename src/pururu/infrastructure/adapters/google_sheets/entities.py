from dataclasses import dataclass


@dataclass
class AttendanceSheet:
    SHEET = "Asistencia"
    DATA_ROW_INIT = 4
    DATA_COL_INIT = "A"
    DATA_COL_END = "R"

    session_id: str
    game_id: int | None
    absence: list[str]  # TRUE/FALSE
    unjustified: list[str]  # TRUE/FALSE
    motives: list[str]
    date: str
    description: str

    def to_row_values(self):
        row = [self.session_id, self.description, self.date]
        for i in range(len(self.absence)):
            row.append(self.absence[i])
            row.append(self.unjustified[i])
            row.append(self.motives[i] if i < len(self.motives) else "")
        return row


@dataclass
class ClockingSheet:
    SHEET = "Fichaje"
    DATA_ROW_INIT = 3
    DATA_COL_INIT = "A"
    DATA_COL_END = "F"

    game_id: int
    playtimes: list[int]

    def to_row_values(self):
        row = [self.game_id]
        row.extend(self.playtimes)
        return row
