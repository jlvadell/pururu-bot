from datetime import datetime

from pururu.common import logger
from pururu.config import settings
from pururu.domain.entities.session import (Session, Status, Type)
from pururu.domain.exceptions import (SessionNotFoundException, SessionAlreadyConcludedException,
                                      CannotConcludeSessionException)
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import SessionConcludeRequestedEvent, SessionConcludedEvent
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

    def register_player_connection(self, player_id: str, time: datetime) -> None:
        """
        Registers a player connection at the given time. If there is no active session, creates a new one.
        :param player_id: the player who connected
        :param time: datetime of connection
        :return: None
        """
        self.logger.debug(f"Registering player '{player_id}' connection at '{time}'",
                          extra={'player_id': player_id, 'time': time.isoformat()})
        session = self.session_repository.find_active_session()
        if not session:
            self.logger.debug(f"No active session found, creating a new one for player '{player_id}'",
                              extra={'player_id': player_id})
            self._create_session(player_id, time)
            return
        self.logger.debug(f"Active session '{session.id}' found, registering player '{player_id}' connection",
                          extra={'session_id': session.id, 'player_id': player_id})
        session.register_player_connection(player_id, time)
        self.session_repository.update(session)

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
        session.register_player_disconnection(player_id, time)
        session = self.session_repository.update(session)
        if not session.any_player_connected():
            self.logger.info(f"No players connected in session '{session.id}', concluding session",
                             extra={'session_id': session.id})
            self.event_bus.publish(SessionConcludeRequestedEvent(datetime.now(), session.id, time))

    def conclude_session(self, session_id: str, end_time: datetime) -> None:
        """
        Concludes the session with the given id at end_time
        :param session_id: the id of the session to conclude
        :param end_time: the time of session conclusion
        :return: None
        """
        self.logger.debug(f"Concluding session '{session_id}' at '{end_time}'",
                          extra={'session_id': session_id, 'end_time': end_time.isoformat()})
        session = self.session_repository.find_by_id(session_id)
        if not session:
            self.logger.error(f"Cannot conclude session '{session_id}' because it does not exist",
                              extra={'session_id': session_id})
            raise SessionNotFoundException(f"Session with id '{session_id}' not found")
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
            type=Type.OFFICIAL_GAME,
            status=Status.DRAFT,
            players=[],
            version=1
        )
        for player in players:
            session.register_player_connection(player.id, start_time if player.id == player_id else None, True)
        self.logger.info(f"Created session '{session_id}' started by '{player_id}'", extra={'session_id': session_id})
        return self.session_repository.save(session)
