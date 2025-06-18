from datetime import datetime
from typing import Optional

import pururu.config as config
from pururu.common import utils, logger
from pururu.common.exceptions import (CannotStartNewGame, CannotEndGame, GameEndedWithoutPrecondition,
                                      DiscordServiceException)
from pururu.domain.current_session import CurrentSession
from pururu.domain.entities import BotEvent, Attendance, MemberAttendance, Clocking, AttendanceEventType, MemberStats, \
    Poll, SessionInfo, Message
from pururu.domain.poll_system.poll_resolution_factory import PollResolutionFactory
from pururu.domain.services.database_service import DatabaseInterface
from pururu.domain.services.discord_service import DiscordInterface


class PururuService:
    def __init__(self, database_service: DatabaseInterface):
        self.logger = logger.get_logger(__name__)
        self.current_session = CurrentSession()
        self.database_service = database_service
        self.poll_resolution_factory: Optional[PollResolutionFactory] = None
        self.discord_service: Optional[DiscordInterface] = None

    def set_discord_service(self, discord_service: DiscordInterface) -> None:
        """
        Sets the discord service
        :param discord_service: DiscordInterface
        :return: None
        """
        self.discord_service = discord_service
        self.poll_resolution_factory = PollResolutionFactory(discord_service)

    def register_bot_event(self, event: BotEvent) -> None:
        """
        Logs a bot event in the database
        :param event: BotEvent
        :return: None
        """
        if not config.DISCORD_EVENT_LOG_ENABLED:
            self.logger.debug("Ignoring bot event, logging disabled",
                              extra={"event_type": event.event_type, "event_data": event.payload})
            return
        self.logger.debug("Registering bot event", extra={"event_type": event.event_type, "event_data": event.payload})
        message = Message(event.description, config.DISCORD_EVENT_LOG_CHANNEL_ID)
        # TODO: this should be async
        self.discord_service.send_message(message)

    def get_session_info(self) -> SessionInfo:
        """
        Retrieves the list of players in the current game
        :return: list[str]
        """
        return SessionInfo(self.current_session.game_id, self.current_session.get_players())

    def add_player(self, player: str, time: datetime) -> None:
        """
        Registers a clock in for a player in the current game
        :param player: player name
        :param time: time of clock in
        :return: None
        """
        self.logger.debug("Player clocked in", extra={"player": player, "time": utils.format_time(time)})
        self.current_session.clock_in(player, time)

    def should_start_new_game_session(self) -> bool:
        """
        Checks if the current game should start based on the current session state
        :return: bool True if the game should start; False otherwise
        """
        return self.current_session.should_start_new_game()

    def remove_player(self, player: str, time: datetime) -> None:
        """
        Registers a clock out for a player in the current game
        :param player: player string
        :param time: time of clock out
        :return: None
        """
        self.logger.debug("Player clock out", extra={"player": player, "time": utils.format_time(time)})
        self.current_session.clock_out(player, time)

    def should_end_game_session(self) -> bool:
        """
        Checks if the current game should end based on the current session state
        :return: bool True if the game should end; False otherwise
        """
        return self.current_session.should_end_game()

    def calculate_player_stats(self, player: str) -> MemberStats:
        """
        Calculates the stats of a player based on the attendance list
        :param player: player name
        :return: MemberStats
        """
        attendance_list = self.database_service.get_all_attendances()
        coins = self.database_service.get_player_coins(player)
        member_stats = MemberStats(player, len(attendance_list), 0, 0, 0, coins)
        for attendance in attendance_list:
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

    def start_new_game(self, start_time: datetime) -> SessionInfo | None:
        """
        Locally creates a new game (attendance) and stores it in the current_session attribute
        :param start_time: start time of the game
        :return: SessionInfo: game_id and players of the new game
        :raises CannotStartNewGame: if the conditions to start a new game are not met
        """
        if not self.current_session.should_start_new_game():
            self.logger.warning("Cannot start new game, conditions not met", extra={
                "current_players": self.current_session.get_players(),
                "game_id": self.current_session.game_id
            })
            raise CannotStartNewGame(
                f"Start game condition not met, current players: {self.current_session.get_players()}, game_id: {self.current_session.game_id}")
        game_id = self.__get_new_game_id()
        self.logger.debug("Starting new game", extra={"game_id": game_id})
        self.current_session.adjust_players_clocking_start_time(start_time)
        self.current_session.game_id = game_id
        return SessionInfo(self.current_session.game_id, self.current_session.get_players())

    def end_game(self, end_time: datetime) -> Attendance | None:
        """
        Ends the current game and stores the attendance and clocking in the database
        :param end_time: end time of the game
        :return: Attendance: attendance of the session
        :raises CannotEndGame: if the conditions to end the game are not met
        :raises GameEndedWithoutPrecondition: if the attendance is not enough to end the game
        """
        if not self.current_session.should_end_game():
            self.logger.warning("Cannot end game, conditions not met", extra={
                "current_players": self.current_session.get_players(),
                "total_players": len(self.current_session.get_players()),
                "required_players": config.MIN_ATTENDANCE_MEMBERS,
                "game_id": self.current_session.game_id
            })
            raise CannotEndGame(f"End game condition not met, current players: {self.current_session.get_players()}, "
                                f"current game info {self.current_session}")
        members = []
        playtime = []
        self.current_session.adjust_players_clocking_end_time(end_time)
        player_attendance_count = 0
        for player in config.PLAYERS:
            player_attended = self.__has_player_attended(player)
            if player_attended:
                player_attendance_count += 1
            playtime.append(self.current_session.get_player_time(player))
            members.append(MemberAttendance(player, player_attended, player_attended, ""))

        clocking = Clocking(self.current_session.game_id, playtime)
        attendance = Attendance(self.current_session.game_id, members, utils.get_current_time_formatted(),
                                AttendanceEventType.OFFICIAL_GAME)
        self.current_session.reset()
        if player_attendance_count < config.MIN_ATTENDANCE_MEMBERS:
            self.logger.warning("Game ended without enough attendance", extra={
                "attendance_count": player_attendance_count,
                "min_required": config.MIN_ATTENDANCE_MEMBERS
            })
            raise GameEndedWithoutPrecondition(
                f"Attendance not enough, attendance count: {player_attendance_count}; min required: {config.MIN_ATTENDANCE_MEMBERS}")
        self.database_service.upsert_attendance(attendance)
        self.database_service.upsert_clocking(clocking)
        return attendance

    async def create_poll(self, poll: Poll) -> Poll:
        """
        Creates a new poll
        :param poll: Poll
        :return: poll, created poll
        """
        self.logger.debug("Creating poll", extra={"question": poll.question, "channel_id": poll.channel_id})
        poll = await self.discord_service.send_poll(poll)
        self.current_session.add_new_poll(poll)
        return poll

    async def get_expired_polls(self) -> list[Poll]:
        """
        Checks if any polls have expired and ends them
        :return: list of expired polls
        """
        expired_polls = []
        polls: list[Poll] = self.current_session.get_expired_polls()
        for poll in polls:
            self.logger.debug("Poll expired", extra={"poll_id": poll.message_id})
            try:
                resulting_poll = await self.discord_service.fetch_poll(poll.channel_id, poll.message_id)
                resulting_poll.resolution_type = poll.resolution_type
                expired_polls.append(resulting_poll)
            except DiscordServiceException as e:
                self.logger.warning("Unable to fetch poll", extra={"poll_id": poll.message_id, "error": str(e)})
                self.current_session.remove_poll(poll.message_id)
        return expired_polls

    async def finalize_poll(self, poll: Poll) -> None:
        """
        Handles the poll resolution
        :param poll: Poll
        :return: None
        """
        strategy = self.poll_resolution_factory.get_strategy(poll.resolution_type)
        await strategy.resolve(poll)
        self.current_session.remove_poll(poll.message_id)
        self.logger.debug("Poll has been resolved", extra={"poll_id": poll.message_id})

    def __has_player_attended(self, player) -> bool:
        """
        Checks if a player meets the conditions to be considered as attended
        :param player: player name
        :return: bool
        """
        playtime = self.current_session.get_player_time(player)
        return playtime >= config.MIN_ATTENDANCE_TIME

    def __get_new_game_id(self) -> int:
        """
        Calculates the new game id
        :return: int
        """
        last_attendance = self.database_service.get_last_attendance()
        return int(last_attendance.game_id) + 1
