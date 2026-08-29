import json
import random
from datetime import datetime, timedelta

from pururu.common import logger
from pururu.config import settings
from pururu.domain.entities.session import (Session, Status, Type, PlayerSession, SessionMetadataKey, Interval)
from pururu.domain.exceptions import (SessionNotFoundException, SessionAlreadyConcludedException,
                                      CannotConcludeSessionException, PlayerNotConnectedException,
                                      OptimisticLockingFailureException)
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import (SessionConcludeRequestedEvent, SessionConcludedEvent,
                                                           SessionUpdatedEvent, SessionCreatedEvent)
from pururu.domain.repositories.session_repository import SessionRepository
from pururu.domain.services.id_generator_service import IdGeneratorService
from pururu.domain.services.player_service import PlayerService
from pururu.domain.services.season_service import SeasonService


class SessionService:
    def __init__(self, session_repository: SessionRepository, season_service: SeasonService,
                 player_service: PlayerService, id_generator: IdGeneratorService, event_bus: EventBus):
        self.session_repository = session_repository
        self.season_service = season_service
        self.player_service = player_service
        self.id_generator = id_generator
        self.event_bus = event_bus
        self.logger = logger.get_logger(__name__)

    def register_player_connection(self, player_id: str, time: datetime) -> Session:
        """
        Registers a player connection at the given time. If there is no active session, creates a new one.
        :param player_id: the player who connected
        :param time: datetime of connection
        :return: the active session
        """
        self.logger.debug(f"Registering player '{player_id}' connection at '{time}'",
                          extra={'player_id': player_id, 'time': time.isoformat()})
        session = self.session_repository.find_active_session()
        if not session:
            self.logger.debug(f"No active session found, creating a new one for player '{player_id}'",
                              extra={'player_id': player_id})
            return self._create_session(player_id, time)
        self.logger.debug(f"Active session '{session.id}' found, registering player '{player_id}' connection",
                          extra={'session_id': session.id, 'player_id': player_id})
        session.register_player_connection(player_id, time)
        return self.session_repository.update(session)

    def register_player_disconnection(self, player_id: str, time: datetime) -> None:
        """
        Registers a player disconnection at the given time. If no players remain connected, concludes the session.
        :param player_id: the player who disconnected
        :param time: the datetime of disconnection
        :return: None
        """
        self.logger.debug(f"Registering player '{player_id}' disconnection at '{time}'",
                          extra={'player_id': player_id, 'time': time.isoformat()})
        session = self.session_repository.find_active_session()
        if not session:
            self.logger.error(f"Player '{player_id}' disconnection at '{time}' but no active session found",
                              extra={'player_id': player_id})
            return
        self.logger.debug(f"Active session '{session.id}' found, registering player '{player_id}' disconnection",
                          extra={'session_id': session.id, 'player_id': player_id})
        try:
            session.register_player_disconnection(player_id, time)
            session = self.session_repository.update(session)
            if not session.any_player_connected():
                self.logger.info(f"No players connected in session '{session.id}', concluding session",
                                 extra={'session_id': session.id})
                self.event_bus.publish(SessionConcludeRequestedEvent(datetime.now(), session.id, time))
        except PlayerNotConnectedException:
            self.logger.warning(
                f"player '{player_id}' disconnection from session {session.id} at '{time}' but player was not connected")

    def conclude_session(self, session_id: str, end_time: datetime) -> None:
        """
        Concludes the session with the given id at end_time
        :param session_id: the id of the session to conclude
        :param end_time: the time of session conclusion
        :return: None
        """
        self.logger.debug(f"Concluding session '{session_id}' at '{end_time}'",
                          extra={'session_id': session_id, 'end_time': end_time.isoformat()})
        session = self.find_session_by_id(session_id)
        try:
            session.conclude(end_time, settings.general.min_attendance_members, settings.general.min_attendance_time)
        except SessionAlreadyConcludedException:
            self.logger.error(f"Session '{session_id}' is already concluded"
                              , extra={'session_id': session_id}, exc_info=True)
            return
        except CannotConcludeSessionException:
            self.logger.error(f"Cannot conclude session '{session_id}' because it does not meet conclusion criteria"
                              , extra={'session_id': session_id}, exc_info=True)
            return
        self.session_repository.update(session)
        self.logger.info(f"Session '{session_id}' concluded successfully", extra={'session_id': session_id})
        self.event_bus.publish(SessionConcludedEvent(datetime.now(), session.id))

    def find_session_by_id(self, session_id: str) -> Session:
        """
        Finds a session by its id
        :param session_id: the id of the session to find
        :return: the found session
        :raises SessionNotFoundException: if no session with the given id exists
        """
        session = self.session_repository.find_by_id(session_id)
        if not session:
            self.logger.error(f"Session '{session_id}' not found", extra={'session_id': session_id})
            raise SessionNotFoundException(f"Session with id '{session_id}' not found")
        return session

    def add_session_metadata(self, session_id: str, updates: dict[SessionMetadataKey, str]) -> None:
        """
        Adds metadata to the session with the given id
        :param session_id: the id of the session to add metadata to
        :param updates: dictionary of metadata keys and values to update
        :return: None
        :raises SessionNotFoundException: if no session with the given id exists
        """
        self.logger.debug(f"Adding metadata updates to session '{session_id}'",
                          extra={'session_id': session_id, 'updates': {k.value: v for k, v in updates.items()}})
        session = self.find_session_by_id(session_id)
        session.metadata.update(updates)
        session.increment_version()
        self.session_repository.update(session)

    def record_player_game(self, player_id: str, game_name: str) -> None:
        """
        Records a game observed for a player in the active session.
        Ignored when there is no active session, the player is not currently connected, or the game was set manually.
        """
        for attempt in range(3):
            session = self.session_repository.find_active_session()
            if not session:
                self.logger.debug(f"Ignoring game observation for player '{player_id}'; no active session",
                                  extra={'player_id': player_id, 'game_name': game_name})
                return
            player_session = session.get_player(player_id)
            if player_session is None or not player_session.is_online():
                self.logger.debug(
                    f"Ignoring game observation for player '{player_id}' in session '{session.id}'; player is not in call",
                    extra={'session_id': session.id, 'player_id': player_id, 'game_name': game_name})
                return
            previous_game = session.get_game_name()
            if not session.record_game_observation(player_id, game_name):
                return
            session.increment_version()
            try:
                self.session_repository.update(session)
            except OptimisticLockingFailureException:
                self.logger.warning(
                    f"Optimistic lock while recording game for session '{session.id}', retry {attempt + 1}",
                    extra={'session_id': session.id, 'player_id': player_id, 'game_name': game_name})
                continue
            if session.get_game_name() != previous_game:
                self.logger.info(f"Session '{session.id}' game detected as '{session.get_game_name()}'",
                                 extra={'session_id': session.id, 'game_name': session.get_game_name(),
                                        'player_id': player_id})
                self.event_bus.publish(SessionUpdatedEvent(datetime.now(), session.id))
            return
        self.logger.error(f"Failed to record game observation for player '{player_id}' after retries",
                          extra={'player_id': player_id, 'game_name': game_name})

    def set_session_game(self, session_id: str, game_name: str) -> None:
        """
        Manually sets the game of the session. Manual values are not overwritten by auto-detection.
        """
        session = self.find_session_by_id(session_id)
        if not session.set_game_name_manual(game_name):
            return
        session.increment_version()
        self.session_repository.update(session)
        self.logger.info(f"Session '{session_id}' game set manually to '{session.get_game_name()}'",
                         extra={'session_id': session_id, 'game_name': session.get_game_name()})
        self.event_bus.publish(SessionUpdatedEvent(datetime.now(), session.id))

    def change_session_type(self, session_id: str, new_type: Type) -> None:
        """
        Changes the type of the session with the given id to new_type
        :param session_id: the id of the session to change
        :param new_type: the new type to set
        :return: None
        :raises SessionNotFoundException: if no session with the given id exists
        """
        self.logger.debug(f"Changing session '{session_id}' type to '{new_type.value}'",
                          extra={'session_id': session_id})
        session = self.find_session_by_id(session_id)
        if session.type == new_type:
            self.logger.debug(f"Session '{session_id}' type is already '{new_type.value}', no change made",
                              extra={'session_id': session_id, 'type': new_type.value})
            return
        session.type = new_type
        session.increment_version()
        self.session_repository.update(session)
        self.event_bus.publish(SessionUpdatedEvent(datetime.now(), session.id))

    def edit_session_attendance(self, session_id: str, player_sessions: list[PlayerSession]) -> None:
        """
        Edits the player attendance data for the session with the given id. Just updates the justification and motive.
        :param session_id: the id of the session to edit
        :param player_sessions: ignoring intervals, the updated player sessions to set
        :return: None
        """
        self.logger.debug(f"Editing session '{session_id}' attendance", extra={'session_id': session_id})
        any_changes = False
        session = self.find_session_by_id(session_id)
        for player in player_sessions:
            player_to_update = session.get_player(player.player_id)
            if player_to_update.attended:
                # Already attended players don't need justification or motive
                continue
            if (player_to_update.justified_absence != player.justified_absence or
                    player_to_update.motive != player.motive):
                any_changes = True
                player_to_update.justified_absence = player.justified_absence
                player_to_update.motive = player.motive
        if any_changes:
            session.increment_version()
            self.session_repository.update(session)
            self.event_bus.publish(SessionUpdatedEvent(datetime.now(), session.id))

    def repair_session_attendance(self, session_id: str, player_ids: list[str]) -> None:
        """
        Repairs incomplete Discord connection data for confirmed attendees.

        Each repaired player's total playtime is brought up to their average playtime in other completed sessions.
        Existing intervals are retained and only non-overlapping simulated intervals are added. If the player has no
        usable history, the minimum attendance time is used as a conservative fallback. The whole session is then
        recalculated, allowing a discarded session to become completed.
        :param session_id: the concluded session to repair
        :param player_ids: players confirmed to have attended
        :return: None
        """
        session = self.find_session_by_id(session_id)
        if not session.is_concluded():
            raise CannotConcludeSessionException(
                f"Session '{session_id}' cannot be repaired before it is concluded")

        repaired_players: dict[str, dict[str, int]] = {}
        repair_candidates: list[PlayerSession] = []
        for player_id in dict.fromkeys(player_ids):
            player_session = session.get_player(player_id)
            if player_session is None:
                self.logger.warning(f"Ignoring unknown player '{player_id}' in attendance repair",
                                    extra={'session_id': session_id, 'player_id': player_id})
                continue
            if player_session.attended:
                continue

            average_playtime, sample_count = self._get_player_average_playtime(player_id, session_id)
            target_playtime = max(average_playtime, settings.general.min_attendance_time)
            target_playtime = min(target_playtime, int((session.end_time - session.start_time).total_seconds()))
            current_playtime = player_session.get_total_time(session.start_time, session.end_time)
            simulated_seconds = self._add_simulated_playtime(
                player_session, session.start_time, session.end_time, target_playtime - current_playtime)
            repair_candidates.append(player_session)
            repaired_players[player_id] = {
                "historical_sessions": sample_count,
                "target_playtime_seconds": target_playtime,
                "simulated_seconds": simulated_seconds,
            }

        if not repair_candidates:
            return

        # Guard against official-session cropping making a repaired player fall below the threshold.
        official_start = session.get_official_start_time(settings.general.min_attendance_members)
        official_end = session.get_official_end_time(settings.general.min_attendance_members)
        for player_session in repair_candidates:
            cropped_playtime = player_session.get_total_time(official_start, official_end)
            extra_seconds = self._add_simulated_playtime(
                player_session, official_start, official_end,
                settings.general.min_attendance_time - cropped_playtime)
            repaired_players[player_session.player_id]["simulated_seconds"] += extra_seconds

        if not any(repair["simulated_seconds"] > 0 for repair in repaired_players.values()):
            return

        session.recalculate_attendance(settings.general.min_attendance_members,
                                       settings.general.min_attendance_time)
        self._record_attendance_repairs(session, repaired_players)
        self.session_repository.update(session)
        self.event_bus.publish(SessionUpdatedEvent(datetime.now(), session.id))

    def _get_player_average_playtime(self, player_id: str, exclude_session_id: str) -> tuple[int, int]:
        sessions = self.session_repository.find_completed_by_player_id(player_id, exclude_session_id)
        playtimes = []
        for historic_session in sessions:
            player_session = historic_session.get_player(player_id)
            if player_session is None:
                continue
            official_start = historic_session.get_official_start_time(settings.general.min_attendance_members)
            official_end = historic_session.get_official_end_time(settings.general.min_attendance_members)
            playtime = player_session.get_total_time(official_start, official_end)
            if playtime > 0:
                playtimes.append(playtime)
        if not playtimes:
            return settings.general.min_attendance_time, 0
        return int(sum(playtimes) / len(playtimes)), len(playtimes)

    @staticmethod
    def _add_simulated_playtime(player_session: PlayerSession, window_start: datetime, window_end: datetime,
                                requested_seconds: int) -> int:
        """Adds requested seconds into free gaps without overlapping the player's recorded intervals."""
        if requested_seconds <= 0 or window_end <= window_start:
            return 0

        occupied = []
        for interval in player_session.intervals:
            if interval.end is None or interval.end <= window_start or interval.start >= window_end:
                continue
            occupied.append((max(interval.start, window_start), min(interval.end, window_end)))
        occupied.sort(key=lambda value: value[0])

        merged = []
        for start, end in occupied:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        gaps = []
        cursor = window_start
        for start, end in merged:
            if cursor < start:
                gaps.append((cursor, start))
            cursor = max(cursor, end)
        if cursor < window_end:
            gaps.append((cursor, window_end))

        remaining = requested_seconds
        added = 0
        for start, end in gaps:
            gap_seconds = int((end - start).total_seconds())
            seconds = min(remaining, gap_seconds)
            if seconds <= 0:
                continue
            reusable_interval = next(
                (interval for interval in player_session.intervals
                 if interval.start == start and interval.end == start), None)
            if reusable_interval:
                reusable_interval.end = start + timedelta(seconds=seconds)
            else:
                player_session.intervals.append(Interval(start=start, end=start + timedelta(seconds=seconds)))
            added += seconds
            remaining -= seconds
            if remaining == 0:
                break
        player_session.intervals.sort(key=lambda interval: interval.start)
        return added

    @staticmethod
    def _record_attendance_repairs(session: Session, repaired_players: dict[str, dict[str, int]]) -> None:
        serialized_repairs = session.metadata.get(SessionMetadataKey.ATTENDANCE_REPAIRS, "{}")
        try:
            repairs = json.loads(serialized_repairs)
        except (TypeError, json.JSONDecodeError):
            repairs = {}
        repairs.update(repaired_players)
        session.metadata[SessionMetadataKey.ATTENDANCE_REPAIRS] = json.dumps(repairs, sort_keys=True)

    def _create_session(self, player_id: str, start_time: datetime) -> Session:
        """
        Creates a new session with the given player as attended from start_time
        :param player_id: the player whose connection started the session
        :param start_time: time of session start (player connection time)
        :return: the created session
        """
        session_id = self.id_generator.next_id()
        season = self.season_service.get_current_season()
        players = self.player_service.get_players()
        session = Session(
            id=session_id,
            season_id=season.id,
            start_time=start_time,
            end_time=None,
            type=self._determine_session_type(start_time),
            status=Status.DRAFT,
            players=[],
            version=1
        )
        for player in players:
            session.register_player_connection(player.id, start_time if player.id == player_id else None, True)
        self.logger.info(f"Created session '{session_id}' started by '{player_id}'", extra={'session_id': session_id})
        created_session = self.session_repository.save(session)
        self.event_bus.publish(SessionCreatedEvent(datetime.now(), created_session.id, created_session.start_time))
        return created_session

    def _determine_session_type(self, start_time: datetime) -> Type:
        """
        Determines the session type based on domain rules
        :param start_time: the start time of the session; can be used to infer the type
        :return: the determined session type
        """
        session_type = Type.ADDITIONAL_GAME
        last_official_game = self.session_repository.find_latest_by_type_and_status(Type.OFFICIAL_GAME,
                                                                                    Status.COMPLETED)
        if last_official_game:
            self.logger.debug(f"Last official game found at '{last_official_game.start_time}'", )
            last_official_game_week = last_official_game.start_time.isocalendar()[1]
            current_week = start_time.isocalendar()[1]
            if last_official_game_week != current_week:
                session_type = self._infer_session_type_from_start_time(start_time)
        return session_type

    def _infer_session_type_from_start_time(self, start_time: datetime) -> Type:
        """
        Infers the session type based on the start time
        :param start_time: the start time of the session
        :return: the inferred session type
        """
        inferred_type = Type.ADDITIONAL_GAME
        if start_time.weekday() == 3:  # Thursday is the de facto day for official games
            inferred_type = Type.OFFICIAL_GAME
        elif start_time.hour >= 21:  # After 9 PM
            if start_time.weekday() in [0, 1]:  # Monday or Tuesday
                if random.random() < 0.25:  # 25% chance
                    inferred_type = Type.OFFICIAL_GAME
            else:
                if random.random() < 0.15:  # 15% chance
                    inferred_type = Type.OFFICIAL_GAME
        self.logger.debug(f"Session type: {inferred_type.value} was inferred from start time '{start_time}'")
        return inferred_type
