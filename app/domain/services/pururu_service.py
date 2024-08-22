from datetime import datetime

import config
from app import utils
from application.events.entities import GameStartedEvent, GameEndedEvent, EndGameIntentEvent, NewGameIntentEvent, \
    MemberJoinedChannelEvent, MemberLeftChannelEvent
from application.events.event_system import EventSystem, EventType
from domain.entities import BotEvent, Attendance, MemberAttendance, Clocking
from domain.services.database_service import DatabaseInterface


class PururuService:
    def __init__(self, database_service: DatabaseInterface, event_system: EventSystem):
        self.database_service = database_service
        self.event_system = event_system
        self.logger = utils.get_logger(__name__)
        self.current_game = {
            "players": {},
            "players_out": {}
        }
        self.players = []

    def handle_voice_state_update(self, member: str, before_channel: str, after_channel: str) -> None:
        """
        Handles the Discord voice state update event
        :param member: member name
        :param before_channel: before_state channel
        :param after_channel: after_state channel
        :return: None
        """
        if member not in config.PLAYERS:
            return
        if before_channel != after_channel:
            if before_channel is None:
                self.event_system.emit_event(EventType.MEMBER_JOINED_CHANNEL,
                                             MemberJoinedChannelEvent(member, after_channel))
            if after_channel is None:
                self.event_system.emit_event(EventType.MEMBER_LEFT_CHANNEL,
                                             MemberLeftChannelEvent(member, before_channel))

    def register_bot_event(self, event: BotEvent) -> None:
        """
        Logs a bot event in the database
        :param event: BotEvent
        :return: None
        """
        self.database_service.insert_bot_event(event)

    def register_new_player(self, player: str) -> None:
        """
        Adds a new player to the current game and if the conditions are met, emit a new game intent
        :param player: player name
        :return: None
        """
        self.logger.info(f"Player {player} added to current game")
        if player not in self.players:
            self.players.append(player)
            if player not in self.current_game['players'].keys():
                self.current_game['players'][player] = utils.get_current_time_formatted()
            self.current_game['players_out'][player] = None

        self.logger.debug(f"Should start new game: {self.__should_start_new_game()}")
        if self.__should_start_new_game():
            self.event_system.emit_event_with_delay(EventType.NEW_GAME_INTENT, NewGameIntentEvent(self.players),
                                                    config.ATTENDANCE_CHECK_DELAY)

    def remove_player(self, player: str) -> None:
        """
        Removes a player from the current game and if the conditions are met, emit an end game intent
        :param player: player string
        :return: None
        """
        if player in self.players:
            self.players.remove(player)
            self.current_game['players_out'][player] = utils.get_current_time_formatted()

        self.logger.debug(f"Player {player} removed from current game, should end game: {self.__should_end_game()}")
        if self.__should_end_game():
            self.event_system.emit_event_with_delay(EventType.END_GAME_INTENT,
                                                    EndGameIntentEvent(self.current_game['game_id'], self.players),
                                                    config.ATTENDANCE_CHECK_DELAY)

    def __should_start_new_game(self) -> bool:
        """
        Checks if the conditions to start a new game are met
        :return: bool
        """
        return "game_id" not in self.current_game.keys() and len(self.players) >= config.MIN_ATTENDANCE_MEMBERS

    def __should_end_game(self) -> bool:
        """
        Checks if the conditions to end the current game are met
        :return: bool
        """
        return "game_id" in self.current_game.keys() and len(self.players) < config.MIN_ATTENDANCE_MEMBERS

    def register_new_game(self) -> None:
        """
        Locally creates a new game (attendance) and stores it in the current_game attribute
        :return: None
        """
        if not self.__should_start_new_game():
            self.logger.debug(f"Start game condition not met, current players: {self.players}, "
                              f"current game info {self.current_game}")
            return
        last_attendance = self.database_service.get_last_attendance()
        self.logger.info(f"Starting new game, last attendance: {last_attendance.game_id}")
        self.current_game['game_id'] = int(last_attendance.game_id) + 1
        self.current_game['players'] = dict()
        self.current_game['players_out'] = dict()
        for player in self.players:
            self.current_game['players'][player] = utils.get_current_time_formatted()
        self.event_system.emit_event(EventType.GAME_STARTED,
                                     GameStartedEvent(self.current_game['game_id'], self.players))

    def end_game(self) -> None:
        """
        Ends the current game and stores the attendance and clocking in the database
        :return: None
        """
        if not self.__should_end_game():
            self.logger.debug(f"End game condition not met, current players: {self.players}, "
                              f"current game info {self.current_game}")
            return
        members = []
        clockings = []
        now = utils.get_current_time_formatted()
        player_attendance_count = 0
        for player in config.PLAYERS:
            player_attended = self.__has_player_attended(player)
            if player_attended:
                player_attendance_count += 1
            if player in self.current_game['players'].keys():
                clockings.append(
                    Clocking(player, self.current_game['game_id'], self.current_game['players'][player],
                             self.current_game['players_out'][player]
                             if self.current_game['players_out'][player] else utils.get_current_time_formatted()))
            members.append(MemberAttendance(player, player_attended, player_attended, ""))

        attendance = Attendance(self.current_game['game_id'], members, now, "Game")
        if player_attendance_count < config.MIN_ATTENDANCE_MEMBERS:
            self.logger.info(f"Attendance not enough, attendance count: {player_attendance_count}; discarding game")
            self.__reset_current_game()
            return
        self.database_service.upsert_attendance(attendance)
        for clocking in clockings:
            self.database_service.insert_clocking(clocking)

        self.__reset_current_game()
        self.event_system.emit_event(EventType.GAME_ENDED, GameEndedEvent(attendance))

    def __has_player_attended(self, player) -> bool:
        """
        Checks if a player meets the conditions to be considered as attended
        :param player: player name
        :return: bool
        """
        if player in self.current_game['players'].keys():
            clock_in = datetime.strptime(self.current_game['players'][player], utils.FORMATTED_TIME_STR)
            clock_out = self.current_game['players_out'][player]
            if clock_out is None:
                clock_out = datetime.now()
            else:
                clock_out = datetime.strptime(clock_out, utils.FORMATTED_TIME_STR)
            return (clock_out - clock_in).total_seconds() >= config.MIN_ATTENDANCE_TIME
        return False

    def __reset_current_game(self) -> None:
        """
        Resets the current game and players attributes
        :return: None
        """
        self.current_game = {
            "players": {},
            "players_out": {}
        }
        self.players = []
