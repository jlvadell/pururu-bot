from datetime import datetime

import pururu.config as config
import pururu.utils as utils
from pururu.application.events.entities import GameStartedEvent, GameEndedEvent, EndGameIntentEvent, \
    NewGameIntentEvent, MemberJoinedChannelEvent, MemberLeftChannelEvent
from pururu.application.events.event_system import EventSystem, EventType
from pururu.domain.entities import BotEvent, Attendance, MemberAttendance, Clocking, AttendanceEventType, MemberStats
from pururu.domain.services.database_service import DatabaseInterface


class CurrentGame:
    def __init__(self):
        self.online_players = set()
        self.players_clock_ins = {}
        self.players_clock_outs = {}
        self.game_id = None
        self.logger = self.logger = utils.get_logger(__name__)

    def clock_in(self, player: str, time: str = None) -> None:
        """
        Clocks in a player
        :param player: member.name
        :param time: time of clock in
        :return: None
        """
        if time is None:
            time = utils.get_current_time_formatted()
        self.online_players.add(player)
        if player not in self.players_clock_ins:
            self.players_clock_ins[player] = []
            self.players_clock_outs[player] = []
        if len(self.players_clock_ins[player]) == len(self.players_clock_outs[player]):
            self.players_clock_ins[player].append(time)

    def clock_out(self, player: str, time: str = None) -> None:
        """
        Clocks out a player
        :param player: member.name
        :param time: time of clock out
        :return: None
        """
        if time is None:
            time = utils.get_current_time_formatted()
        if player not in self.online_players:
            self.logger.error(f"Player {player} not found in online_players")
            return
        self.online_players.remove(player)
        if player not in self.players_clock_outs:
            self.logger.error(f"Player {player} not found in clock_outs")
            return
        self.players_clock_outs[player].append(time)

    def get_player_time(self, player: str) -> int:
        """
        Gets the total playtime of a player in seconds.
        :param player: member.name
        :return: int: total playtime in seconds
        """
        if player not in self.players_clock_ins:
            return 0
        clock_ins = self.players_clock_ins[player]
        clock_outs = self.players_clock_outs[player]
        total_time = 0
        for i in range(len(clock_ins)):
            clock_in = datetime.strptime(clock_ins[i], utils.FORMATTED_TIME_STR)
            clock_out = datetime.strptime(clock_outs[i], utils.FORMATTED_TIME_STR) if i < len(
                clock_outs) else datetime.now()
            total_time += (clock_out - clock_in).total_seconds()
        return int(total_time)

    def should_start_new_game(self) -> bool:
        """
        Checks if the conditions to start a new game are met
        :return: bool
        """
        return self.game_id is None and len(self.online_players) >= config.MIN_ATTENDANCE_MEMBERS

    def should_end_game(self) -> bool:
        """
        Checks if the conditions to end the current game are met
        :return: bool
        """
        return self.game_id is not None and len(self.online_players) < config.MIN_ATTENDANCE_MEMBERS

    def get_players(self) -> list:
        """
        Returns the list of the current players
        :return: list
        """
        return list(self.online_players)

    def __str__(self):
        return f"Game {self.game_id}, players {self.online_players}, clock_ins {self.players_clock_ins}, " \
               f"clock_outs {self.players_clock_outs}"

    def reset(self):
        """
        Resets the current game to initial state
        :return: None
        """
        self.__init__()

    def adjust_clocking(self, start_time: datetime = None, end_time: datetime = None) -> None:
        """
        Matches the start_time and end_time of the players to the given times
        :return: None
        """
        if start_time is not None:
            for player in self.players_clock_ins:
                last_start_time = self.get_player_last_start_time(player)
                if last_start_time is None or last_start_time < start_time:
                    last_start_time = start_time
                self.players_clock_ins[player] = [last_start_time.strftime(utils.FORMATTED_TIME_STR)]
        if end_time is not None:
            for player in self.players_clock_outs:
                last_end_time = self.get_player_last_end_time(player)
                if last_end_time is None or last_end_time > end_time:
                    last_end_time = end_time
                self.players_clock_outs[player] = [last_end_time.strftime(utils.FORMATTED_TIME_STR)]

    def get_player_last_start_time(self, player: str) -> datetime|None:
        """
        Gets the last start_time of a player.
        :param player: member.name
        :return: datetime: parsed start_time or None if currently offline
        """
        if player not in self.players_clock_ins:
            return None
        clock_ins = self.players_clock_ins[player]
        clock_outs = self.players_clock_outs[player]
        if len(clock_ins) <= len(clock_outs):
            return None
        last_clock_in = datetime.strptime(clock_ins[-1], utils.FORMATTED_TIME_STR)
        return last_clock_in

    def get_player_last_end_time(self, player: str) -> datetime|None:
        """
        Gets the last end_time of a player.
        :param player: member.name
        :return: datetime: parsed end_time or None if currently online or not clocked in
        """
        if player not in self.players_clock_outs:
            return None
        clock_ins = self.players_clock_ins[player]
        clock_outs = self.players_clock_outs[player]
        if len(clock_ins) > len(clock_outs):
            return None
        last_clock_out = datetime.strptime(clock_outs[-1], utils.FORMATTED_TIME_STR)
        return last_clock_out


class PururuService:
    def __init__(self, database_service: DatabaseInterface, event_system: EventSystem):
        self.database_service = database_service
        self.event_system = event_system
        self.logger = utils.get_logger(__name__)
        self.current_game = CurrentGame()

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
        self.current_game.clock_in(player)

        self.logger.debug(f"Should start new game: {self.current_game.should_start_new_game()}")
        if self.current_game.should_start_new_game():
            self.event_system.emit_event_with_delay(EventType.NEW_GAME_INTENT,
                                                    NewGameIntentEvent(self.current_game.get_players(), datetime.now()),
                                                    config.ATTENDANCE_CHECK_DELAY)

    def remove_player(self, player: str) -> None:
        """
        Removes a player from the current game and if the conditions are met, emit an end game intent
        :param player: player string
        :return: None
        """
        self.logger.info(f"Player {player} disconnected")
        self.current_game.clock_out(player)

        self.logger.debug(f"Player {player} removed from current game, should end game: "
                          f"{self.current_game.should_end_game()}")
        if self.current_game.should_end_game():
            self.event_system.emit_event_with_delay(EventType.END_GAME_INTENT,
                                                    EndGameIntentEvent(self.current_game.game_id,
                                                                       self.current_game.get_players(),
                                                                       datetime.now()),
                                                    config.ATTENDANCE_CHECK_DELAY)

    def register_new_game(self, start_time: datetime) -> None:
        """
        Locally creates a new game (attendance) and stores it in the current_game attribute
        :param start_time: start time of the game
        :return: None
        """
        if not self.current_game.should_start_new_game():
            self.logger.debug(f"Start game condition not met, current players: {self.current_game.get_players()}, "
                              f"current game info {self.current_game}")
            return
        last_attendance = self.database_service.get_last_attendance()
        self.logger.info(f"Starting new game, last attendance: {last_attendance.game_id}")
        self.current_game.adjust_clocking(start_time=start_time)
        self.current_game.game_id = int(last_attendance.game_id) + 1
        self.event_system.emit_event(EventType.GAME_STARTED,
                                     GameStartedEvent(self.current_game.game_id, self.current_game.get_players()))

    def end_game(self, end_time: datetime) -> None:
        """
        Ends the current game and stores the attendance and clocking in the database
        :param end_time: end time of the game
        :return: None
        """
        if not self.current_game.should_end_game():
            self.logger.debug(f"End game condition not met, current players: {self.current_game.get_players()}, "
                              f"current game info {self.current_game}")
            return
        members = []
        playtimes = []
        self.current_game.adjust_clocking(end_time=end_time)
        player_attendance_count = 0
        for player in config.PLAYERS:
            player_attended = self.__has_player_attended(player)
            if player_attended:
                player_attendance_count += 1
            playtimes.append(self.current_game.get_player_time(player))
            members.append(MemberAttendance(player, player_attended, player_attended, ""))

        clocking = Clocking(self.current_game.game_id, playtimes)
        attendance = Attendance(self.current_game.game_id, members, utils.get_current_time_formatted(),
                                AttendanceEventType.OFFICIAL_GAME)
        if player_attendance_count < config.MIN_ATTENDANCE_MEMBERS:
            self.logger.info(f"Attendance not enough, attendance count: {player_attendance_count}; discarding game")
            self.current_game.reset()
            return
        self.database_service.upsert_attendance(attendance)
        self.database_service.insert_clocking(clocking)

        self.current_game.reset()
        self.event_system.emit_event(EventType.GAME_ENDED, GameEndedEvent(attendance))

    def __has_player_attended(self, player) -> bool:
        """
        Checks if a player meets the conditions to be considered as attended
        :param player: player name
        :return: bool
        """
        playtime = self.current_game.get_player_time(player)
        return playtime >= config.MIN_ATTENDANCE_TIME
