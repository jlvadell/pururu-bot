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

    def points(self) -> int:
        if self == AttendanceEventType.OFFICIAL_GAME:
            return 2
        if self == AttendanceEventType.ADDITIONAL_OFFICIAL_GAME:
            return 2
        if self == AttendanceEventType.OFFICIAL_MEETING:
            return 3
        return 0

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

class MonthlyReport:
    def __init__(self, month: int, total_events: int, games, members):
        self.month = month
        self.total_events = total_events
        self.games = games
        self.members = members
        pass

    def as_message(self) -> str:
        text = f"Reporte del mes {self.month}:\n"
        text += f"Ha habido un total de {self.total_events} eventos.\n\n"
        text += f"-- Se ha jugado a los siguientes juegos:\n"
        for key_game in self.games:
            text += f"--- ID del juego: {key_game}, Veces: {self.games[key_game]}\n"
        text += f"-- Estos han sido los miembros participantes:\n"
        for key_member in self.members:
            text += f"--- Nombre: {key_member}, Asistencias: {self.members[key_member]['attendance']}, " 
            text += f"Justificaciones: {self.members[key_member]['justified']}\n"
        text += "Fin del reporte."
        return text

class MemberStats:
    def __init__(self, member: str, total_events: int, absences: int, justifications: int, points: int, coins: int):
        self.member = member
        self.total_events = total_events
        self.absences = absences
        self.justifications = justifications
        self.points = points
        self.absent_events: list[int] = []
        self.coins = coins

    def as_message(self) -> str:
        return f"Total de eventos: {self.total_events}\n" \
               f"Asistencias: {self.total_events - self.absences}\n" \
               f"Faltas: {self.absences}\n" \
               f"Injustificadas: {self.absences - self.justifications}\n" \
               f"Justificadas: {self.justifications}\n" \
               f"Puntos: {self.points}\n" \
               f"Eventos ausentes (Ids): {', '.join(map(str, self.absent_events))}\n" \
               f"KeroCoins: {self.coins}"
