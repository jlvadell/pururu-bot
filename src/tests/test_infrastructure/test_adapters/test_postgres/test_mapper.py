from datetime import datetime, date
from unittest.mock import patch

import pytest
from hamcrest import assert_that, equal_to, instance_of

from pururu.domain.entities.player import Player
from pururu.domain.entities.poll import PollReference, PollResolutionType
from pururu.domain.entities.season import Season
from pururu.domain.entities.session import Session, Status, Type, PlayerSession, Interval
from pururu.infrastructure.adapters.postgres.entities import (
    SessionRecord, PlayerSessionRecord, PlayerSessionIntervalRecord,
    PlayerRecord, SeasonRecord
)
from pururu.infrastructure.adapters.postgres.mapper import PostgresMapper
from tests.test_domain.conftest import session, player_session, player, season


# ============================================================================
# Session Mapping Tests
# ============================================================================

@pytest.mark.unit
@patch('pururu.infrastructure.adapters.postgres.mapper.datetime')
def test_map_session_to_record(mock_datetime, session, player_session):
    """Test mapping Session to SessionRecord"""
    # Arrange
    fixed_time = datetime(2025, 10, 2, 12, 0, 0)
    mock_datetime.now.return_value = fixed_time
    session.players = [player_session]

    # Act
    result = PostgresMapper.map_session_to_record(session)

    # Assert
    assert_that(result, instance_of(SessionRecord))
    assert_that(result.session_id, equal_to("session123"))
    assert_that(result.season_id, equal_to("season456"))
    assert_that(result.type, equal_to("Official Game"))
    assert_that(result.status, equal_to("Draft"))
    assert_that(result.version, equal_to(1))
    assert_that(len(result.players), equal_to(1))


@pytest.mark.unit
def test_map_record_to_session():
    """Test mapping SessionRecord to Session"""
    # Arrange
    record = SessionRecord(
        session_id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=datetime(2025, 10, 1, 12, 0, 0),
        type="Official Game",
        status="Completed",
        version=2,
        last_updated=datetime.now()
    )
    record.players = []

    # Act
    result = PostgresMapper.map_record_to_session(record)

    # Assert
    assert_that(result, instance_of(Session))
    assert_that(result.id, equal_to("session123"))
    assert_that(result.season_id, equal_to("season456"))
    assert_that(result.type, equal_to(Type.OFFICIAL_GAME))
    assert_that(result.status, equal_to(Status.COMPLETED))
    assert_that(result.version, equal_to(2))


@pytest.mark.unit
@patch('pururu.infrastructure.adapters.postgres.mapper.datetime')
def test_update_record_from_session(mock_datetime):
    """Test updating SessionRecord from Session"""
    # Arrange
    fixed_time = datetime(2025, 10, 2, 15, 0, 0)
    mock_datetime.now.return_value = fixed_time

    existing_record = SessionRecord(
        session_id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type="Official Game",
        status="Draft",
        version=1,
        last_updated=datetime(2025, 10, 1, 10, 0, 0)
    )
    existing_record.players = [
        PlayerSessionRecord(
            session_id="session123",
            player_id="player123",
            justified_absence=True,
            attended=None,
            motive=None,
            intervals=[
                PlayerSessionIntervalRecord(
                    session_id="session123",
                    player_id="player123",
                    join_time=datetime(2025, 10, 1, 10, 0, 0),
                    leave_time=None)
            ]
        )
    ]

    updated_session = Session(
        id="session123",
        season_id="season789",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=datetime(2025, 10, 1, 12, 0, 0),
        type=Type.ADDITIONAL_GAME,
        status=Status.COMPLETED,
        players=[
            PlayerSession("player123", True, False, "some motive",
                          [Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 12, 0, 0), )])
        ],
        version=2
    )

    # Act
    result = PostgresMapper.update_record_from_session(existing_record, updated_session)

    # Assert
    assert_that(result.season_id, equal_to("season789"))
    assert_that(result.end_time, equal_to(datetime(2025, 10, 1, 12, 0, 0)))
    assert_that(result.type, equal_to("Additional Game"))
    assert_that(result.status, equal_to("Completed"))
    assert_that(result.version, equal_to(2))
    assert_that(result.last_updated, equal_to(fixed_time))
    assert_that(len(result.players), equal_to(1))

    player = result.players[0]
    assert_that(player.player_id, equal_to("player123"))
    assert_that(player.justified_absence, equal_to(False))
    assert_that(player.attended, equal_to(True))
    assert_that(player.motive, equal_to("some motive"))
    assert_that(len(player.intervals), equal_to(1))

    interval = player.intervals[0]
    assert_that(interval.join_time, equal_to(datetime(2025, 10, 1, 10, 0, 0)))
    assert_that(interval.leave_time, equal_to(datetime(2025, 10, 1, 12, 0, 0)))


# ============================================================================
# PlayerSession Mapping Tests
# ============================================================================

@pytest.mark.unit
def test_map_player_session_to_record(player_session):
    """Test mapping PlayerSession to PlayerSessionRecord"""
    # Act
    result = PostgresMapper.map_player_session_to_record(player_session, "session123")

    # Assert
    assert_that(result, instance_of(PlayerSessionRecord))
    assert_that(result.session_id, equal_to("session123"))
    assert_that(result.player_id, equal_to("player123"))
    assert_that(result.justified_absence, equal_to(False))
    assert_that(result.attended, equal_to(True))
    assert_that(result.motive, equal_to(None))
    assert_that(len(result.intervals), equal_to(2))


@pytest.mark.unit
def test_map_record_to_player_session():
    """Test mapping PlayerSessionRecord to PlayerSession"""
    # Arrange
    record = PlayerSessionRecord(
        session_id="session123",
        player_id="player123",
        justified_absence=True,
        attended=False,
        motive="sick"
    )
    record.intervals = []

    # Act
    result = PostgresMapper.map_record_to_player_session(record)

    # Assert
    assert_that(result, instance_of(PlayerSession))
    assert_that(result.player_id, equal_to("player123"))
    assert_that(result.justified_absence, equal_to(True))
    assert_that(result.attended, equal_to(False))
    assert_that(result.motive, equal_to("sick"))


# ============================================================================
# Interval Mapping Tests
# ============================================================================

@pytest.mark.unit
def test_map_interval_to_record():
    """Test mapping Interval to PlayerSessionIntervalRecord"""
    # Arrange
    interval = Interval(
        start=datetime(2025, 10, 1, 10, 0, 0),
        end=datetime(2025, 10, 1, 11, 0, 0)
    )

    # Act
    result = PostgresMapper.map_interval_to_record(interval, "session123", "player123")

    # Assert
    assert_that(result, instance_of(PlayerSessionIntervalRecord))
    assert_that(result.session_id, equal_to("session123"))
    assert_that(result.player_id, equal_to("player123"))
    assert_that(result.join_time, equal_to(datetime(2025, 10, 1, 10, 0, 0)))
    assert_that(result.leave_time, equal_to(datetime(2025, 10, 1, 11, 0, 0)))


@pytest.mark.unit
def test_map_record_to_interval():
    """Test mapping PlayerSessionIntervalRecord to Interval"""
    # Arrange
    record = PlayerSessionIntervalRecord(
        session_id="session123",
        player_id="player123",
        join_time=datetime(2025, 10, 1, 10, 0, 0),
        leave_time=datetime(2025, 10, 1, 11, 0, 0)
    )

    # Act
    result = PostgresMapper.map_record_to_interval(record)

    # Assert
    assert_that(result, instance_of(Interval))
    assert_that(result.start, equal_to(datetime(2025, 10, 1, 10, 0, 0)))
    assert_that(result.end, equal_to(datetime(2025, 10, 1, 11, 0, 0)))


# ============================================================================
# Player Mapping Tests
# ============================================================================

@pytest.mark.unit
def test_map_player_to_record(player):
    """Test mapping Player to PlayerRecord"""
    # Act
    result = PostgresMapper.map_player_to_record(player)

    # Assert
    assert_that(result, instance_of(PlayerRecord))
    assert_that(result.player_id, equal_to("player123"))
    assert_that(result.display_name, equal_to("TestPlayer"))
    assert_that(result.birthday, equal_to(date(1990, 1, 1)))


@pytest.mark.unit
def test_map_record_to_player():
    """Test mapping PlayerRecord to Player"""
    # Arrange
    record = PlayerRecord(
        player_id="player123",
        display_name="TestPlayer",
        birthday=date(1990, 1, 1)
    )

    # Act
    result = PostgresMapper.map_record_to_player(record)

    # Assert
    assert_that(result, instance_of(Player))
    assert_that(result.id, equal_to("player123"))
    assert_that(result.name, equal_to("TestPlayer"))
    assert_that(result.birthday, equal_to(date(1990, 1, 1)))


# ============================================================================
# Season Mapping Tests
# ============================================================================

@pytest.mark.unit
def test_map_season_to_record(season):
    """Test mapping Season to SeasonRecord"""
    # Act
    result = PostgresMapper.map_season_to_record(season)

    # Assert
    assert_that(result, instance_of(SeasonRecord))
    assert_that(result.season_id, equal_to("season123"))
    assert_that(result.president_id, equal_to("president456"))
    assert_that(result.start_date, equal_to(datetime(2025, 1, 1, 0, 0, 0)))
    assert_that(result.end_date, equal_to(None))


@pytest.mark.unit
def test_map_record_to_season():
    """Test mapping SeasonRecord to Season"""
    # Arrange
    record = SeasonRecord(
        season_id="season123",
        president_id="president456",
        start_date=datetime(2025, 1, 1, 0, 0, 0),
        end_date=datetime(2025, 12, 31, 23, 59, 59)
    )

    # Act
    result = PostgresMapper.map_record_to_season(record)

    # Assert
    assert_that(result, instance_of(Season))
    assert_that(result.id, equal_to("season123"))
    assert_that(result.president_id, equal_to("president456"))
    assert_that(result.start_date, equal_to(datetime(2025, 1, 1, 0, 0, 0)))
    assert_that(result.end_date, equal_to(datetime(2025, 12, 31, 23, 59, 59)))


# ============================================================================
# Poll Mapping Tests
# ============================================================================

@pytest.mark.unit
def test_map_poll_to_record():
    """Test mapping PollReference to PollRecord"""
    # Arrange
    poll = PollReference(
        id="poll123",
        channel_id="channel123",
        expires_at=datetime(2025, 10, 1, 10, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE
    )

    # Act
    result = PostgresMapper.map_poll_to_record(poll)

    # Assert
    assert_that(result.id, equal_to("poll123"))
    assert_that(result.channel_id, equal_to("channel123"))
    assert_that(result.expires_at, equal_to(datetime(2025, 10, 1, 10, 0, 0)))
    assert_that(result.resolution_type, equal_to(PollResolutionType.SEND_MESSAGE.value))


@pytest.mark.unit
def test_map_record_to_poll():
    """Test mapping PollRecord to PollReference"""
    from pururu.infrastructure.adapters.postgres.entities import PollRecord

    # Arrange
    record = PollRecord(
        id="poll123",
        channel_id="channel123",
        expires_at=datetime(2025, 10, 1, 10, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE.value
    )

    # Act
    result = PostgresMapper.map_record_to_poll(record)

    # Assert
    assert_that(result.id, equal_to("poll123"))
    assert_that(result.channel_id, equal_to("channel123"))
    assert_that(result.expires_at, equal_to(datetime(2025, 10, 1, 10, 0, 0)))
    assert_that(result.resolution_type, equal_to(PollResolutionType.SEND_MESSAGE))
