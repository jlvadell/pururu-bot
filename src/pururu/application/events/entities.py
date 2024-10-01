from datetime import datetime
from enum import Enum

import pururu.utils as utils
from pururu.domain.entities import BotEvent, Attendance, Poll


class EventType(Enum):
    MEMBER_JOINED_CHANNEL = "member_joined_channel"
    MEMBER_LEFT_CHANNEL = "member_left_channel"
    NEW_GAME_INTENT = "new_game_intent"
    END_GAME_INTENT = "end_game_intent"
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    CHECK_EXPIRED_POLLS = "check_expired_polls"
    FINALIZE_POLL = "finalize_poll"


class PururuEvent:
    def __init__(self, event_type: EventType, description: str):
        self.event_type = event_type
        self.created_at = utils.get_current_time_formatted()
        self.description = description

    def as_bot_event(self) -> BotEvent:
        return BotEvent(self.event_type.value, self.created_at, self.description)

    def __str__(self):
        return f"{self.event_type}-{self.created_at}: {self.description}"


class MemberJoinedChannelEvent(PururuEvent):
    def __init__(self, member: str, channel: str, joined_at: datetime):
        super().__init__(EventType.MEMBER_JOINED_CHANNEL,
                         f'member {member} has joined channel {channel} at {joined_at}')
        self.member = member
        self.channel = channel
        self.joined_at = joined_at


class MemberLeftChannelEvent(PururuEvent):
    def __init__(self, member: str, channel: str, left_at: datetime):
        super().__init__(EventType.MEMBER_LEFT_CHANNEL,
                         f'member {member} has left channel {channel} at {left_at}')
        self.member = member
        self.channel = channel
        self.left_at = left_at


class NewGameIntentEvent(PururuEvent):
    def __init__(self, players: list[str], start_time: datetime):
        super().__init__(EventType.NEW_GAME_INTENT,
                         f'players: {players}, start_time {start_time}')
        self.players = players
        self.start_time = start_time


class EndGameIntentEvent(PururuEvent):
    def __init__(self, game_id: int, players: list[str], end_time: datetime):
        super().__init__(EventType.END_GAME_INTENT,
                         f'game_id: {game_id}, players: {players}, end_time {end_time}')
        self.game_id = game_id
        self.players = players
        self.end_time = end_time


class GameStartedEvent(PururuEvent):
    def __init__(self, game_id: int, players: list[str]):
        super().__init__(EventType.GAME_STARTED, f'game_id: {game_id}, players: {players}')
        self.game_id = game_id
        self.players = players


class GameEndedEvent(PururuEvent):
    def __init__(self, attendance: Attendance):
        super().__init__(EventType.GAME_ENDED, f'game_id: {attendance.game_id}, '
                                               f'attended: {[member.member for member in attendance.members if member.attendance]}, '
                                               f'absences: {[member.member for member in attendance.members if not member.attendance]}')
        self.attendance = attendance


class CheckExpiredPollsEvent(PururuEvent):
    def __init__(self):
        super().__init__(EventType.CHECK_EXPIRED_POLLS, 'checking expired polls')


class FinalizePollEvent(PururuEvent):
    def __init__(self, poll: Poll):
        super().__init__(EventType.FINALIZE_POLL, f'finalizing poll {poll.question}, winners: {poll.get_winners()}')
        self.poll = poll
