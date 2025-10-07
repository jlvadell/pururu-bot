"""Shared fixtures for domain tests - domain entities and value objects"""
from datetime import datetime, date
from unittest.mock import MagicMock

import pytest

from pururu.domain.entities.player import Player
from pururu.domain.entities.poll import Poll, PollResolutionType
from pururu.domain.entities.season import Season
from pururu.domain.entities.session import Session, PlayerSession, Interval, Type, Status


@pytest.fixture
def player():
    """Create a sample Player entity"""
    return Player(
        id="player123",
        name="TestPlayer",
        birthday=date(1990, 1, 1)
    )


@pytest.fixture
def player_session():
    """Create a sample PlayerSession"""
    return PlayerSession(
        player_id="player123",
        justified_absence=False,
        attended=True,
        motive=None,
        intervals=[
            Interval(start=datetime(2025, 10, 1, 10, 0, 0), end=datetime(2025, 10, 1, 11, 0, 0)),
            Interval(start=datetime(2025, 10, 1, 11, 30, 0), end=datetime(2025, 10, 1, 12, 0, 0))
        ]
    )

@pytest.fixture
def player_session_absent():
    """Create  PlayerSession absent unjustified"""
    return PlayerSession(
        player_id="player456",
        justified_absence=False,
        attended=False,
        motive=None,
        intervals=[]
    )

@pytest.fixture
def player_session_justified():
    """Create  PlayerSession absent justified"""
    return PlayerSession(
        player_id="player456",
        justified_absence=True,
        attended=False,
        motive="He's away on a trip.",
        intervals=[]
    )

@pytest.fixture
def player_session_online():
    """Create a sample PlayerSession"""
    return PlayerSession(
        player_id="player123",
        justified_absence=False,
        attended=False,
        motive=None,
        intervals=[
            Interval(start=datetime(2025, 10, 1, 10, 0, 0), end=datetime(2025, 10, 1, 11, 0, 0)),
            Interval(start=datetime(2025, 10, 1, 11, 30, 0), end=None)
        ]
    )


@pytest.fixture
def session():
    """Create a sample Session entity"""
    return Session(
        id="session123",
        season_id="season456",
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[],
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None
    )


@pytest.fixture
def on_going_session(player_session_online):
    """Create a completed Session with players"""
    return Session(
        id="session123",
        season_id="season456",
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[player_session_online],
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None
    )

@pytest.fixture
def completed_session(player_session):
    """Create a completed Session with players"""
    return Session(
        id="session123",
        season_id="season456",
        type=Type.OFFICIAL_GAME,
        status=Status.COMPLETED,
        players=[player_session],
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=datetime(2025, 10, 1, 12, 0, 0)
    )


@pytest.fixture
def season():
    """Create a sample Season entity"""
    return Season(
        id="season123",
        president_id="president456",
        start_date=datetime(2025, 1, 1, 0, 0, 0),
        end_date=None
    )


@pytest.fixture
def poll():
    """Create a sample Poll entity"""
    return Poll(
        id="poll123",
        channel_id="channel456",
        expires_at=datetime(2025, 10, 2, 12, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE,
        question="What game should we play?",
        answers=["Game A", "Game B", "Game C"],
        duration_hours=24,
        allow_multiple=False,
        results={"Game A": 5, "Game B": 3, "Game C": 2}
    )


@pytest.fixture
def mock_session_service():
    """Create a mock SessionService"""
    return MagicMock()


@pytest.fixture
def mock_player_service():
    """Create a mock PlayerService"""
    return MagicMock()


@pytest.fixture
def mock_season_service():
    """Create a mock SeasonService"""
    return MagicMock()


@pytest.fixture
def mock_poll_service():
    """Create a mock PollService"""
    return MagicMock()


