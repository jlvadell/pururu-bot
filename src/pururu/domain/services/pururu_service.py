from datetime import datetime

import pururu.config as config
import pururu.utils as utils
from pururu.application.events.entities import GameStartedEvent, GameEndedEvent, EndGameIntentEvent, \
    NewGameIntentEvent, MemberJoinedChannelEvent, MemberLeftChannelEvent
from pururu.application.events.event_system import EventSystem, EventType
from pururu.domain.current_session import CurrentSession
from pururu.domain.entities import BotEvent, Attendance, MemberAttendance, Clocking, AttendanceEventType, MemberStats
from pururu.domain.services.database_service import DatabaseInterface


class PururuService:
    def __init__(self, database_service: DatabaseInterface, event_system: EventSystem):
        self.database_service = database_service
        self.event_system = event_system
        self.logger = utils.get_logger(__name__)
        self.current_session = CurrentSession()

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

    def retrieve_player_stats(self, player: str) -> MemberStats:
        """
        Retrieves the attendance stats of a player
        :param player: player name
        :return: MemberStats
        """
        self.logger.debug(f"Retrieving stats for player {player}")
        attendances = self.database_service.get_all_attendances()
        coins = self.database_service.get_player_coins(player)
        member_stats = MemberStats(player, len(attendances), 0, 0, 0, coins)
        for attendance in attendances:
            member_attendance = next((m for m in attendance.members if m.member == player), None)

            if member_attendance:
                if member_attendance.attendance:
                    member_stats.points += attendance.event_type.points()
                else:
                    member_stats.absences += 1
                    member_stats.absent_events.append(attendance.game_id)
                    if member_attendance.justified:
                        member_stats.justifications += 1
                        member_stats.points += 1
        return member_stats

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
        self.logger.info(f"Player {player} connected")
        self.current_session.clock_in(player)

        if self.current_session.should_start_new_game():
            self.logger.debug(f"Start game condition met, current players: {self.current_session.get_players()}")
            self.event_system.emit_event_with_delay(EventType.NEW_GAME_INTENT,
                                                    NewGameIntentEvent(self.current_session.get_players(),
                                                                       datetime.now()), config.ATTENDANCE_CHECK_DELAY)

    def remove_player(self, player: str) -> None:
        """
        Removes a player from the current game and if the conditions are met, emit an end game intent
        :param player: player string
        :return: None
        """
        self.logger.info(f"Player {player} disconnected")
        self.current_session.clock_out(player)

        if self.current_session.should_end_game():
            self.logger.debug(f"End game condition met, current players: {self.current_session.get_players()}")
            self.event_system.emit_event_with_delay(EventType.END_GAME_INTENT,
                                                    EndGameIntentEvent(self.current_session.game_id,
                                                                       self.current_session.get_players(),
                                                                       datetime.now()),
                                                    config.ATTENDANCE_CHECK_DELAY)

    def register_new_game(self, start_time: datetime) -> None:
        """
        Locally creates a new game (attendance) and stores it in the current_session attribute
        :param start_time: start time of the game
        :return: None
        """
        if not self.current_session.should_start_new_game():
            self.logger.debug(f"Start game condition not met, current players: {self.current_session.get_players()}, "
                              f"current game info {self.current_session}")
            return
        last_attendance = self.database_service.get_last_attendance()
        self.logger.info(f"Starting new game, last attendance: {last_attendance.game_id}")
        self.current_session.adjust_players_clocking_start_time(start_time)
        self.current_session.game_id = int(last_attendance.game_id) + 1
        self.event_system.emit_event(EventType.GAME_STARTED,
                                     GameStartedEvent(self.current_session.game_id, self.current_session.get_players()))

    def end_game(self, end_time: datetime) -> None:
        """
        Ends the current game and stores the attendance and clocking in the database
        :param end_time: end time of the game
        :return: None
        """
        if not self.current_session.should_end_game():
            self.logger.debug(f"End game condition not met, current players: {self.current_session.get_players()}, "
                              f"current game info {self.current_session}")
            return
        members = []
        playtimes = []
        self.current_session.adjust_players_clocking_end_time(end_time)
        player_attendance_count = 0
        for player in config.PLAYERS:
            player_attended = self.__has_player_attended(player)
            if player_attended:
                player_attendance_count += 1
            playtimes.append(self.current_session.get_player_time(player))
            members.append(MemberAttendance(player, player_attended, player_attended, ""))

        clocking = Clocking(self.current_session.game_id, playtimes)
        attendance = Attendance(self.current_session.game_id, members, utils.get_current_time_formatted(),
                                AttendanceEventType.OFFICIAL_GAME)
        if player_attendance_count < config.MIN_ATTENDANCE_MEMBERS:
            self.logger.info(f"Attendance not enough, attendance count: {player_attendance_count}; discarding game")
            return
        self.database_service.upsert_attendance(attendance)
        self.database_service.insert_clocking(clocking)

        self.current_session.reset()
        self.event_system.emit_event(EventType.GAME_ENDED, GameEndedEvent(attendance))

    def __has_player_attended(self, player) -> bool:
        """
        Checks if a player meets the conditions to be considered as attended
        :param player: player name
        :return: bool
        """
        playtime = self.current_session.get_player_time(player)
        return playtime >= config.MIN_ATTENDANCE_TIME
