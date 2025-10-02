from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pururu.domain.exceptions import (SessionAlreadyConcludedException, CannotConcludeSessionException)


class Type(Enum):
    OFFICIAL_GAME = "Official Game"
    ADDITIONAL_GAME = "Additional Game"
    OFFICIAL_MEETING = "Official Meeting"

    def __str__(self):
        return self.value


class Status(Enum):
    DRAFT = "Draft"
    COMPLETED = "Completed"
    DISCARDED = "Discarded"

    def __str__(self):
        return self.value


@dataclass
class Interval:
    start: datetime
    end: datetime | None = None

    def get_time(self) -> int:
        """
        Returns the total time in seconds of the interval; if the interval is not closed (end is None), returns -1
        :return: total seconds
        """
        if self.end is None:
            return -1
        return int((self.end - self.start).total_seconds())


@dataclass
class PlayerSession:
    player_id: str
    justified_absence: bool
    motive: str | None
    intervals: list[Interval]

    def get_total_time(self, crop_initial: datetime | None = None, crop_final: datetime | None = None) -> int:
        """
        Returns the total time in seconds of the player session, optionally cropped to a given interval
        :param crop_initial: if provided, only intervals that end after this time are considered
        :param crop_final: if provided, only intervals that start before this time are considered
        :return: total seconds
        """
        total_time = 0
        for interval in self.intervals:
            if crop_initial and interval.end and interval.end <= crop_initial:
                continue
            if crop_final and interval.start >= crop_final:
                continue
            start = max(interval.start, crop_initial) if crop_initial else interval.start
            end = min(interval.end, crop_final) if (crop_final and interval.end) else interval.end
            if end is None:
                continue
            total_time += int((end - start).total_seconds())
        return total_time

    def has_attended(self, min_time: int = 1800, start_time: datetime | None = None,
                     end_time: datetime | None = None) -> bool:
        """
        Returns True if the player has attended the session (i.e., total time >= min_time)
        :param min_time: minimum time in seconds to consider attendance (default 1800 seconds = 30 minutes)
        :param start_time: if provided, only intervals that end after this time are considered
        :param end_time: if provided, only intervals that start before this time are considered
        :return: bool
        """
        return self.get_total_time(start_time, end_time) >= min_time


@dataclass
class Session:
    id: str
    season_id: str
    start_time: datetime
    end_time: datetime | None
    type: Type
    status: Status
    players: list[PlayerSession]
    version: int = 1  # For optimistic locking

    def was_concluded_positively(self) -> bool:
        """
        Returns True if the session was concluded positively (i.e., status is COMPLETED)
        :return: bool
        """
        return self.status == Status.COMPLETED

    def any_player_connected(self) -> bool:
        """
        Returns True if any player is currently connected (i.e., has an open interval)
        :return: bool
        """
        return any(ps.intervals and ps.intervals[-1].end is None for ps in self.players)

    def get_player(self, player_id: str) -> PlayerSession | None:
        """
        Returns the player session for the given player id, or None if not found
        :param player_id: the player id
        :return: PlayerSession or None
        """
        return next((ps for ps in self.players if ps.player_id == player_id), None)

    def add_player(self, player_id: str, justified_absence: bool = False, motive: str = "") -> PlayerSession:
        """
        Adds a player to the session with the given justified absence and motive; no intervals are added
        if the player is already in the session, does nothing
        :param player_id: the player id
        :param justified_absence: whether the absence is justified
        :param motive: the motive for the absence
        :return: player session
        """
        player_session = self.get_player(player_id)
        if player_session:
            return player_session
        player_session = PlayerSession(player_id=player_id, justified_absence=justified_absence, motive=motive,
                                       intervals=[])
        self.players.append(player_session)
        return player_session

    def register_player_connection(self, player_id: str, connection_time: datetime | None,
                                   skip_version_increment=False) -> None:
        """
        Registers a player connection at the given time or just adds the player if connection_time is None
        :param player_id: the player id
        :param connection_time: datetime of the connection; if None just registers the player without interval
        :param skip_version_increment: if True, does not increment the version (used when creating a new session)
        :return: None
        """
        player_session = self.add_player(player_id)
        if player_session.intervals and player_session.intervals[-1].end is None:
            # player already connected; close previous interval
            player_session.intervals[-1].end = connection_time
        if connection_time:
            player_session.intervals.append(Interval(start=connection_time))
        if not skip_version_increment:
            self.increment_version()

    def register_player_disconnection(self, player_id: str, disconnection_time: datetime) -> None:
        """
        Registers a player disconnection at the given time
        :param player_id: the player id
        :param disconnection_time: datetime of the disconnection
        :return: None
        """
        player_session = self.get_player(player_id)
        if player_session is None or not player_session.intervals or player_session.intervals[-1].end is not None:
            # player not found or not connected
            return
        player_session.intervals[-1].end = disconnection_time
        self.increment_version()

    def is_concluded(self) -> bool:
        """
        Returns True if the session is concluded (i.e., has an end time, and status is not DRAFT)
        :return: bool
        """
        return self.end_time is not None and self.status != Status.DRAFT

    def get_official_start_time(self, min_players: int = 3) -> datetime:
        """
        Returns the official start time of the session, by default a session starts when the third player joins, and it's at than time that the session is considered started.
        :return: datetime of the third player's join time, or session start time if less than min_players joined
        """
        players_ordered = self._get_players_session_join_ordered()
        if len(players_ordered) < min_players:
            return self.start_time
        return players_ordered[min_players - 1].intervals[0].start

    def get_official_end_time(self, min_players: int = 3) -> datetime | None:
        """
        Returns the official end time of the session, by default a session ends when the third last player leaves, and it's at than time that the session is considered ended.
        :return: datetime of the third last player's leave time, or session end time (can be None) if less than min_players joined
        """
        players_ordered = self._get_players_session_left_ordered()
        if len(players_ordered) < min_players:
            return self.end_time
        return players_ordered[-min_players].intervals[-1].end

    def get_official_player_count(self, min_playtime: int = 1800, official_start_time: datetime | None = None,
                                  official_end_time: datetime | None = None) -> int:
        """
        Returns the official player count of the session, by default a player is considered to have attended if they have at least 30 minutes (1800 seconds) of total time in the session
        :param min_playtime: minimum playtime in seconds to consider attendance (default 1800 seconds = 30 minutes)
        :param official_start_time: official start time
        :param official_end_time: official end time
        :return: int
        """
        return sum(1 for ps in self.players if ps.has_attended(min_playtime, official_start_time, official_end_time))

    def conclude(self, end_time: datetime, min_players: int = 3, min_playtime: int = 1800) -> None:
        """
        Concludes the session at the given end_time, closing any open player intervals
        :param end_time: the datetime of session conclusion
        :param min_players: minimum number of players required for the session to be considered valid (default 3)
        :param min_playtime: minimum playtime in seconds required for a player to be considered
        :raises SessionAlreadyConcludedException: if the session is already concluded
        :raises CannotConcludeSessionException: if the session cannot be concluded
        :return: None
        """
        if self.is_concluded():
            raise SessionAlreadyConcludedException(f"Session '{self.id}' is already concluded")
        if not self.can_conclude():
            raise CannotConcludeSessionException(
                f"Session '{self.id}' cannot be concluded because conditions are not met")
        self.end_time = end_time
        self.status = Status.COMPLETED
        official_start_time = self.get_official_start_time(min_players)
        official_end_time = self.get_official_end_time(min_players)
        duration = int((official_end_time - official_start_time).total_seconds())
        official_player_count = self.get_official_player_count(min_playtime, official_start_time, official_end_time)

        if duration < min_playtime or official_player_count < min_players:
            self.status = Status.DISCARDED
        self.increment_version()

    def can_conclude(self) -> bool:
        """
        Returns True if the session can be concluded (i.e., no players are currently connected)
        :return: bool
        """
        return not self.any_player_connected()

    def increment_version(self) -> None:
        """
        Increments the version of the session for optimistic locking
        :return: None
        """
        self.version += 1

    def _get_players_session_join_ordered(self) -> list[PlayerSession]:
        """
        Returns the list of player sessions ordered by join time (first interval start time), excluding players with no intervals
        :return: list of PlayerSession
        """
        return sorted(
            [ps for ps in self.players if ps.intervals],
            key=lambda ps: ps.intervals[0].start
        )

    def _get_players_session_left_ordered(self) -> list[PlayerSession]:
        """
        Returns the list of player sessions ordered by leave time (last interval end time), excluding players with no intervals or no ended intervals
        :return: list of PlayerSession
        """
        return sorted(
            [ps for ps in self.players if ps.intervals and ps.intervals[-1].end],
            key=lambda ps: ps.intervals[-1].end
        )
