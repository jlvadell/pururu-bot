from datetime import datetime
from typing import Optional

import pururu.config as config
import pururu.utils as utils
from domain.exceptions import DiscordServiceException
from pururu.domain.current_session import CurrentSession
from pururu.domain.entities import BotEvent, Attendance, MemberAttendance, Clocking, AttendanceEventType, MemberStats, \
    Poll, SessionInfo
from pururu.domain.exceptions import CannotStartNewGame, CannotEndGame, GameEndedWithoutPrecondition
from pururu.domain.poll_system.poll_resolution_factory import PollResolutionFactory
from pururu.domain.services.database_service import DatabaseInterface
from pururu.domain.services.discord_service import DiscordInterface


class PururuService:
    def __init__(self, database_service: DatabaseInterface):
        self.logger = utils.get_logger(__name__)
        self.current_session = CurrentSession()
        self.database_service = database_service
        self.poll_resolution_factory: Optional[PollResolutionFactory] = None
        self.discord_service = None

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
        self.logger.debug(f"Registering bot event: {event}")
        self.database_service.insert_bot_event(event)

    def get_session_info(self) -> SessionInfo:
        """
        Retrieves the list of players in the current game
        :return: list[str]
        """
        return SessionInfo(self.current_session.game_id, self.current_session.get_players())

    def add_player(self, player: str, time: datetime) -> bool:
        """
        Adds a new player to the current game and returns a check to see if the conditions are met to start a new game
        :param player: player name
        :param time: time of clock in
        :return: bool True if a new game should be started; False otherwise
        """
        self.logger.debug(f"Player {player} clock in {time}")
        self.current_session.clock_in(player, time)

        return self.current_session.should_start_new_game()

    def remove_player(self, player: str, time: datetime) -> bool:
        """
        Removes a player from the current game and returns a check to see if the conditions are met to end the game
        :param player: player string
        :param time: time of clock out
        :return: bool True if the game should end; False otherwise
        """
        self.logger.debug(f"Player {player} clock out {time}")
        self.current_session.clock_out(player, time)

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
            raise CannotStartNewGame(
                f"Start game condition not met, current players: {self.current_session.get_players()}, game_id: {self.current_session.game_id}")
        game_id = self.__get_new_game_id()
        self.logger.debug(f"Starting new game, {game_id}")
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
        self.logger.info(f"Creating poll: {poll.question}")
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
            self.logger.debug(f"Poll {poll.message_id} has expired")
            try:
                resulting_poll = await self.discord_service.fetch_poll(poll.channel_id, poll.message_id)
                resulting_poll.resolution_type = poll.resolution_type
                expired_polls.append(resulting_poll)
            except DiscordServiceException as e:
                self.logger.warn(f"Unable to fetch poll {poll.message_id}; {e}")
                self.current_session.remove_poll(poll.message_id)
        return expired_polls

    async def finalize_poll(self, poll: Poll) -> None:
        """
        Handles the poll resolution
        :param poll: Poll
        :return: None
        """
        await self.poll_resolution_factory.get_strategy(poll.resolution_type).resolve(poll)
        self.current_session.remove_poll(poll.message_id)
        self.logger.debug(f"Poll {poll.message_id} has been resolved")

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
