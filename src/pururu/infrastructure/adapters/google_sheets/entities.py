class BotEventSheet:
    SHEET = "Eventos"
    DATA_ROW_INIT = 2
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
    DATA_ROW_INIT = 4
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

class CoinsSheet:
    SHEET = "Economia"
    DATA_ROW_INIT = 2
    DATA_COL_INIT = "A"
    DATA_COL_END = "E"

    def __init__(self, player: str, coins: int):
        self.player = player
        self.coins = coins

    def to_row_values(self):
        row = [self.description, self.date]
        for i in range(len(self.absence)):
            row.append(self.absence[i])
            row.append(self.unjustified[i])
            row.append(self.motives[i] if i < len(self.motives) else "")
        return row

class ClockingSheet:
    SHEET = "Fichaje"
    DATA_ROW_INIT = 3
    DATA_COL_INIT = "A"
    DATA_COL_END = "F"

    def __init__(self, game_id: int, playtimes: list[int]):
        self.game_id = game_id
        self.playtimes = playtimes

    def to_row_values(self):
        row = [self.game_id]
        row.extend(self.playtimes)
        return row
