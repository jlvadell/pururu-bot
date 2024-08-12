import config
import utils
from application.events.entities import GameStartedEvent, GameEndedEvent, EndGameIntentEvent, NewGameIntentEvent
from application.events.event_system import EventSystem, EventType
from domain.entities import BotEvent, Attendance, MemberAttendance, Clocking
from domain.interfaces.database import DatabaseInterface
from domain.interfaces.pururu_service import PururuInterface


class PururuService(PururuInterface):
    def __init__(self, database_service: DatabaseInterface, event_system: EventSystem):
        self.database_service = database_service
        self.event_system = event_system
        self.logger = utils.get_logger(__name__)
        self.current_game = {
            "players": {},
            "players_out": {}
        }
        self.players = []

    def register_bot_event(self, event: BotEvent):
        """
        Logs a bot event in the database
        :param event: BotEvent
        :return: None
        """
        self.database_service.register_bot_event(event)

    def register_new_player(self, player: str):
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

    def remove_player(self, player: str):
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

    def __should_start_new_game(self):
        """
        Checks if the conditions to start a new game are met
        :return: bool
        """
        return "game_id" not in self.current_game.keys() and len(self.players) >= config.MIN_ATTENDANCE_MEMBERS

    def __should_end_game(self):
        """
        Checks if the conditions to end the current game are met
        :return: bool
        """
        return "game_id" in self.current_game.keys() and len(self.players) < config.MIN_ATTENDANCE_MEMBERS

    def register_new_game(self):
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

    def end_game(self):
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
        for player in config.PLAYERS:
            if player in self.current_game['players'].keys():
                clockings.append(
                    Clocking(player, self.current_game['game_id'], self.current_game['players'][player],
                             self.current_game['players_out'][player]))
            members.append(MemberAttendance(player, player in self.current_game['players'].keys(),
                                            player in self.current_game['players'].keys(), ""))

        attendance = Attendance(self.current_game['game_id'], members, now, "Game")
        self.database_service.upsert_attendance(attendance)
        for clocking in clockings:
            self.database_service.insert_clocking(clocking)

        self.current_game = {
            "players": {},
            "players_out": {}
        }
        self.event_system.emit_event(EventType.GAME_ENDED, GameEndedEvent(attendance))
