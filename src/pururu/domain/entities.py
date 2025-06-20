import hashlib
import json
from enum import Enum
from dataclasses import dataclass

@dataclass()
class BotEvent:
    def __init__(self, event_type: str, created_at: str, description: str, payload: dict):
        self.event_type = event_type
        self.created_at = created_at
        self.description = description
        self.payload = payload

    def get_idempotency_key(self) -> str:
        """
        Generates a deduplication id for the event.
        :return: string containing the deduplication id
        """
        key_data = {
            "event_type": self.event_type,
            "created_at": self.created_at,
            "payload": self.payload
        }

        # Sort keys to guarantee consistent hashing
        json_string = json.dumps(key_data, sort_keys=True)
        hash_object = hashlib.sha256(json_string.encode("utf-8"))

        return hash_object.hexdigest()


@dataclass()
class MemberAttendance:
    def __init__(self, member: str, attendance: bool, justified: bool, motive: str):
        self.member = member
        self.attendance = attendance
        self.justified = justified
        self.motive = motive


@dataclass()
class AttendanceEventType(Enum):
    OFFICIAL_GAME = "Juegueo Oficial"
    ADDITIONAL_OFFICIAL_GAME = "Juegueo Adicional Oficial"
    OFFICIAL_MEETING = "Quedada Oficial"
    UNKNOWN = "unknown"

    def __str__(self):
        return self.value

    def __json__(self):
        return self.value

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


@dataclass()
class Attendance:
    def __init__(self, game_id: int, members: list[MemberAttendance], date: str, event_type: AttendanceEventType):
        self.game_id = game_id
        self.members = members
        self.date = date
        self.event_type = event_type


@dataclass()
class Clocking:
    def __init__(self, game_id: int, playtimes: list[int]):
        self.game_id = game_id
        self.playtimes = playtimes


@dataclass()
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


@dataclass()
class Message:
    def __init__(self, content: str, channel_id: int):
        self.message_id = None
        self.content = content
        self.channel_id = channel_id


@dataclass()
class SessionInfo:
    def __init__(self, game_id: int, players: list[str]):
        self.game_id = game_id
        self.players = players


@dataclass()
class PollResolutionType(Enum):
    SEND_MESSAGE = "SEND_MESSAGE"

    def __str__(self):
        return self.value

    def __json__(self):
        return self.value


@dataclass()
class Poll:
    def __init__(self, question: str, channel_id: int, answers: list[str], duration_hours: int = 24,
                 allow_multiple: bool = False, resolution_type: PollResolutionType = PollResolutionType.SEND_MESSAGE):
        self.message_id = None
        self.question = question
        self.channel_id = channel_id
        self.answers = answers
        self.duration_hours = duration_hours
        self.expires_at = None
        self.allow_multiple = allow_multiple
        self.results = {}
        self.resolution_type = resolution_type

    def get_winners(self) -> str:
        """
        Returns the answer with the most votes, or multiple answers if there is a tie.
        Multiple answers are returned as a comma-separated string.
        :return: answer with the most votes; string
        """
        max_votes = max(self.results.values())
        winners = [answer for answer, votes in self.results.items() if votes == max_votes]
        return ', '.join(winners)
