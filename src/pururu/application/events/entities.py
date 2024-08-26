import pururu.utils as utils
from pururu.application.events.event_system import EventType
from pururu.domain.entities import BotEvent, Attendance


class MemberJoinedChannelEvent:
    def __init__(self, member: str, channel: str):
        self.member = member
        self.channel = channel

    def as_bot_event(self) -> BotEvent:
        return BotEvent(EventType.MEMBER_JOINED_CHANNEL.value, utils.get_current_time_formatted(),
                        f'member {self.member} has joined channel {self.channel}')


class MemberLeftChannelEvent:
    def __init__(self, member: str, channel: str):
        self.member = member
        self.channel = channel

    def as_bot_event(self) -> BotEvent:
        return BotEvent(EventType.MEMBER_LEFT_CHANNEL.value, utils.get_current_time_formatted(),
                        f'member {self.member} has left channel {self.channel}')


class NewGameIntentEvent:
    def __init__(self, players: list[str]):
        self.players = players

    def as_bot_event(self) -> BotEvent:
        return BotEvent(EventType.NEW_GAME_INTENT.value, utils.get_current_time_formatted(),
                        f'players: {self.players}')


class EndGameIntentEvent:
    def __init__(self, game_id: int, players: list[str]):
        self.game_id = game_id
        self.players = players

    def as_bot_event(self) -> BotEvent:
        return BotEvent(EventType.END_GAME_INTENT.value, utils.get_current_time_formatted(),
                        f'game_id: {self.game_id}, players: {self.players}')


class GameStartedEvent:
    def __init__(self, game_id: int, players: list[str]):
        self.game_id = game_id
        self.players = players

    def as_bot_event(self) -> BotEvent:
        return BotEvent(EventType.GAME_STARTED.value, utils.get_current_time_formatted(),
                        f'game_id: {self.game_id}, players: {self.players}')


class GameEndedEvent:
    def __init__(self, attendance: Attendance):
        self.attendance = attendance

    def as_bot_event(self) -> BotEvent:
        return BotEvent(EventType.GAME_ENDED.value, utils.get_current_time_formatted(),
                        f'game_id: {self.attendance.game_id}, '
                        f'attended: {[member.member for member in self.attendance.members if member.attendance]}, '
                        f'absences: {[member.member for member in self.attendance.members if not member.attendance]}')
