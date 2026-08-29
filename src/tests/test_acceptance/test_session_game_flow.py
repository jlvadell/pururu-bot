from datetime import datetime
from unittest.mock import MagicMock

import pytest
from hamcrest import assert_that, equal_to, none, is_

from pururu.domain.entities.session import Session, Status, Type, PlayerSession, Interval, SessionMetadataKey, GameSource
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.repositories.session_repository import SessionRepository
from pururu.domain.services.id_generator_service import IdGeneratorService
from pururu.domain.services.player_service import PlayerService
from pururu.domain.services.season_service import SeasonService
from pururu.domain.services.session_service import SessionService


class InMemorySessionRepository(SessionRepository):
    def __init__(self, session: Session | None = None):
        self.session = session

    def save(self, session: Session) -> Session:
        self.session = session
        return session

    def update(self, session: Session) -> Session:
        self.session = session
        return session

    def find_by_id(self, session_id: str) -> Session | None:
        if self.session and self.session.id == session_id:
            return self.session
        return None

    def find_active_session(self) -> Session | None:
        if self.session and self.session.status == Status.DRAFT and self.session.end_time is None:
            return self.session
        return None

    def find_latest_by_type_and_status(self, session_type: Type, session_status: Status) -> Session | None:
        return None

    def find_completed_by_player_id(self, player_id: str, exclude_session_id: str | None = None) -> list[Session]:
        return []


def _online_player(player_id: str) -> PlayerSession:
    return PlayerSession(
        player_id=player_id,
        attended=False,
        justified_absence=False,
        motive=None,
        intervals=[Interval(start=datetime(2025, 10, 1, 10, 0, 0), end=None)]
    )


def _build_session(players: list[PlayerSession]) -> Session:
    return Session(
        id="session123",
        season_id="season456",
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=players,
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        metadata={}
    )


def _build_service(session: Session) -> tuple[SessionService, InMemorySessionRepository]:
    repository = InMemorySessionRepository(session)
    service = SessionService(
        repository,
        MagicMock(spec=SeasonService),
        MagicMock(spec=PlayerService),
        MagicMock(spec=IdGeneratorService),
        MagicMock(spec=EventBus),
    )
    return service, repository


@pytest.mark.integration
def test_acceptance_detects_majority_game_during_call():
    session = _build_session([_online_player("p1"), _online_player("p2"), _online_player("p3")])
    service, repository = _build_service(session)

    service.record_player_game("p1", "League of Legends")
    service.record_player_game("p2", "League of Legends")
    service.record_player_game("p3", "VALORANT")

    stored = repository.find_by_id("session123")
    assert_that(stored.get_game_name(), equal_to("League of Legends"))
    assert_that(stored.metadata[SessionMetadataKey.GAME_SOURCE], equal_to(GameSource.AUTO.value))


@pytest.mark.integration
def test_acceptance_no_game_when_nobody_reports_activity():
    session = _build_session([_online_player("p1"), _online_player("p2")])
    service, repository = _build_service(session)

    service.record_player_game("p1", "   ")
    service.record_player_game("offline-player", "League of Legends")

    stored = repository.find_by_id("session123")
    assert_that(stored.get_game_name(), none())
    assert_that(stored.metadata.get(SessionMetadataKey.GAME_OBSERVATIONS), none())


@pytest.mark.integration
def test_acceptance_manual_game_overrides_and_locks_auto_detection():
    session = _build_session([_online_player("p1"), _online_player("p2")])
    service, repository = _build_service(session)

    service.record_player_game("p1", "League of Legends")
    service.set_session_game("session123", "Minecraft")
    service.record_player_game("p2", "VALORANT")

    stored = repository.find_by_id("session123")
    assert_that(stored.get_game_name(), equal_to("Minecraft"))
    assert_that(stored.is_game_manually_set(), is_(True))
