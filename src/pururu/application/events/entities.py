from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

from pururu.common import utils
from pururu.domain.entities import BotEvent, Attendance, Poll, AttendanceEventType, MemberAttendance, PollResolutionType


class EventType(Enum):
    """
    Enum representing different types of events in the Pururu application.
    NOTE: AWS QUEUE HAVE FILTERS; REMEMBER TO ADD NEW EVENTS THERE.
    """
    MEMBER_JOINED_CHANNEL = "member_joined_channel"
    MEMBER_LEFT_CHANNEL = "member_left_channel"
    NEW_GAME_INTENT = "new_game_intent"
    END_GAME_INTENT = "end_game_intent"
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    CHECK_EXPIRED_POLLS = "check_expired_polls"
    FINALIZE_POLL = "finalize_poll"

    def __str__(self):
        return self.value

    def __json__(self):
        return self.value

class PururuEvent(ABC):
    def __init__(self, event_type: EventType, description: str):
        self.event_type = event_type
        self.created_at = utils.get_current_time_formatted()
        self.description = description

    def as_bot_event(self) -> BotEvent:
        return BotEvent(
            event_type=self.event_type.value,
            created_at=self.created_at,
            description=self.description,
            payload=self._serialize()
        )

    def _serialize(self) -> dict:
        """
        Converts the event instance into a JSON-serializable dictionary.
        Handles datetime and Enum fields.
        """
        def convert(value):
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [convert(v) for v in value]
            elif isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, Enum):
                return value.value
            else:
                return value

        return {k: convert(v) for k, v in self.__dict__.items()}

    @staticmethod
    @abstractmethod
    def process_payload(payload: dict) -> "PururuEvent":
        """
        Must be implemented by subclasses to convert raw payload into event.
        """
        pass

    def _set_created_at(self, created_at: str):
        self.created_at = created_at

    def __str__(self):
        return f"{self.event_type}-{self.created_at}: {self.description}"

    def get_age(self) -> float:
        """
        Returns the age of the event in seconds
        :return: float - age of the event in seconds
        """
        return (datetime.now() - utils.parse_time(self.created_at)).total_seconds()


class MemberJoinedChannelEvent(PururuEvent):
    def __init__(self, member: str, channel: str, joined_at: datetime):
        super().__init__(EventType.MEMBER_JOINED_CHANNEL,
                         f'member {member} has joined channel {channel} at {joined_at}')
        self.member = member
        self.channel = channel
        self.joined_at = joined_at

    @staticmethod
    def process_payload(payload: dict) -> "MemberJoinedChannelEvent":
        member = payload["member"]
        channel = payload["channel"]
        joined_at = datetime.fromisoformat(payload["joined_at"])
        event = MemberJoinedChannelEvent(member, channel, joined_at)
        event._set_created_at(payload["created_at"])
        return event


class MemberLeftChannelEvent(PururuEvent):
    def __init__(self, member: str, channel: str, left_at: datetime):
        super().__init__(EventType.MEMBER_LEFT_CHANNEL,
                         f'member {member} has left channel {channel} at {left_at}')
        self.member = member
        self.channel = channel
        self.left_at = left_at

    @staticmethod
    def process_payload(payload: dict) -> "MemberLeftChannelEvent":
        member = payload["member"]
        channel = payload["channel"]
        left_at = datetime.fromisoformat(payload["left_at"])
        event = MemberLeftChannelEvent(member, channel, left_at)
        event._set_created_at(payload["created_at"])
        return event


class NewGameIntentEvent(PururuEvent):
    def __init__(self, players: list[str], start_time: datetime):
        super().__init__(EventType.NEW_GAME_INTENT,
                         f'players: {players}, start_time {start_time}')
        self.players = players
        self.start_time = start_time

    @staticmethod
    def process_payload(payload: dict) -> "NewGameIntentEvent":
        players = payload["players"]
        start_time = datetime.fromisoformat(payload["start_time"])
        event = NewGameIntentEvent(players, start_time)
        event._set_created_at(payload["created_at"])
        return event


class EndGameIntentEvent(PururuEvent):
    def __init__(self, game_id: int, players: list[str], end_time: datetime):
        super().__init__(EventType.END_GAME_INTENT,
                         f'game_id: {game_id}, players: {players}, end_time {end_time}')
        self.game_id = game_id
        self.players = players
        self.end_time = end_time

    @staticmethod
    def process_payload(payload: dict) -> "EndGameIntentEvent":
        game_id = payload["game_id"]
        players = payload["players"]
        end_time = datetime.fromisoformat(payload["end_time"])
        event = EndGameIntentEvent(game_id, players, end_time)
        event._set_created_at(payload["created_at"])
        return event


class GameStartedEvent(PururuEvent):
    def __init__(self, game_id: int, players: list[str]):
        super().__init__(EventType.GAME_STARTED, f'game_id: {game_id}, players: {players}')
        self.game_id = game_id
        self.players = players

    @staticmethod
    def process_payload(payload: dict) -> "GameStartedEvent":
        game_id = payload["game_id"]
        players = payload["players"]
        event = GameStartedEvent(game_id, players)
        event._set_created_at(payload["created_at"])
        return event


class GameEndedEvent(PururuEvent):
    def __init__(self, game_id: int, date: str, attendance_event_type: str, members: list[dict]):
        description = f"game_id: {game_id}, " \
                      f"attended: {[m['member'] for m in members if m['attendance']]}, " \
                      f"absences: {[m['member'] for m in members if not m['attendance']]}"
        super().__init__(EventType.GAME_ENDED, description)
        self.game_id = game_id
        self.date = date
        self.attendance_event_type = attendance_event_type
        self.members = members        # list of dicts: [{member, attendance, justified, motive}]

    @staticmethod
    def process_payload(payload: dict) -> "GameEndedEvent":
        game_id = payload["game_id"]
        date = payload["date"]
        attendance_event_type = payload["attendance_event_type"]
        members = payload["members"]
        event = GameEndedEvent(game_id, date, attendance_event_type, members)
        event._set_created_at(payload["created_at"])
        return event

    @staticmethod
    def from_attendance(attendance: Attendance) -> "GameEndedEvent":
        members = [
            {
                "member": m.member,
                "attendance": m.attendance,
                "justified": m.justified,
                "motive": m.motive
            }
            for m in attendance.members
        ]
        return GameEndedEvent(
            game_id=attendance.game_id,
            date=attendance.date,
            attendance_event_type=attendance.event_type.value,
            members=members
        )

    def to_attendance(self) -> Attendance:
        members = [MemberAttendance(**m) for m in self.members]
        return Attendance(self.game_id, members, self.date, AttendanceEventType.of(self.attendance_event_type))


class CheckExpiredPollsEvent(PururuEvent):
    def __init__(self):
        super().__init__(EventType.CHECK_EXPIRED_POLLS, 'checking expired polls')

    @staticmethod
    def process_payload(payload: dict) -> "CheckExpiredPollsEvent":
        event = CheckExpiredPollsEvent()
        event._set_created_at(payload["created_at"])
        return event


class FinalizePollEvent(PururuEvent):
    def __init__(self, question: str, channel_id: int, answers: list[str], results: dict,
                 duration_hours: int, expires_at: str, allow_multiple: bool, resolution_type: str,
                 message_id: int):
        description = f"finalizing poll {question}, results: {results}"
        super().__init__(EventType.FINALIZE_POLL, description)
        self.question = question
        self.channel_id = channel_id
        self.answers = answers
        self.results = results
        self.duration_hours = duration_hours
        self.expires_at = expires_at
        self.allow_multiple = allow_multiple
        self.resolution_type = resolution_type
        self.message_id = message_id

    @staticmethod
    def process_payload(payload: dict) -> "FinalizePollEvent":
        question = payload["question"]
        channel_id = payload["channel_id"]
        answers = payload["answers"]
        results = payload["results"]
        duration_hours = payload["duration_hours"]
        expires_at = payload["expires_at"]
        allow_multiple = payload["allow_multiple"]
        resolution_type = payload["resolution_type"]
        message_id = payload.get("message_id")
        event = FinalizePollEvent(question, channel_id, answers, results, duration_hours, expires_at, allow_multiple,
                                  resolution_type, message_id)
        event._set_created_at(payload["created_at"])
        return event

    @staticmethod
    def from_poll(poll: Poll) -> "FinalizePollEvent":
        return FinalizePollEvent(
            question=poll.question,
            channel_id=poll.channel_id,
            answers=poll.answers,
            results=poll.results,
            duration_hours=poll.duration_hours,
            expires_at=poll.expires_at.isoformat() if poll.expires_at else None,
            allow_multiple=poll.allow_multiple,
            resolution_type=poll.resolution_type.value,
            message_id=poll.message_id
        )

    def to_poll(self) -> Poll:
        poll = Poll(
            question=self.question,
            channel_id=self.channel_id,
            answers=self.answers,
            duration_hours=self.duration_hours,
            allow_multiple=self.allow_multiple,
            resolution_type=PollResolutionType(self.resolution_type)
        )

        poll.message_id = self.message_id
        poll.expires_at = datetime.fromisoformat(self.expires_at) if self.expires_at else None
        poll.results = self.results

        return poll


