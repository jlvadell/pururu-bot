from datetime import datetime

import pytest
from hamcrest import assert_that, equal_to, is_, none

from pururu.domain.entities.session import (
    Session, PlayerSession, Interval, Type, Status
)
from pururu.domain.exceptions import (
    SessionAlreadyConcludedException,
    CannotConcludeSessionException
)


# ============================================================================
# Interval Tests
# ============================================================================

@pytest.mark.unit
def test_interval_get_time_closed():
    """Test Interval.get_time returns duration for closed interval"""
    # Arrange
    interval = Interval(
        start=datetime(2025, 10, 1, 10, 0, 0),
        end=datetime(2025, 10, 1, 11, 0, 0)
    )

    # Act
    result = interval.get_time()

    # Assert
    assert_that(result, equal_to(3600))  # 1 hour = 3600 seconds


@pytest.mark.unit
def test_interval_get_time_open():
    """Test Interval.get_time returns -1 for open interval"""
    # Arrange
    interval = Interval(start=datetime(2025, 10, 1, 10, 0, 0), end=None)

    # Act
    result = interval.get_time()

    # Assert
    assert_that(result, equal_to(-1))


# ============================================================================
# PlayerSession Tests
# ============================================================================

@pytest.mark.unit
def test_player_session_get_total_time():
    """Test PlayerSession.get_total_time sums all intervals"""
    # Arrange
    player_session = PlayerSession(
        player_id="player123",
        attended=True,
        justified_absence=False,
        motive=None,
        intervals=[
            Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 11, 0, 0)),  # 1 hour
            Interval(datetime(2025, 10, 1, 11, 30, 0), datetime(2025, 10, 1, 12, 0, 0))  # 30 minutes
        ]
    )

    # Act
    result = player_session.get_total_time()

    # Assert
    assert_that(result, equal_to(5400))  # 90 minutes = 5400 seconds


@pytest.mark.unit
def test_player_session_get_total_time_with_crop():
    """Test PlayerSession.get_total_time with crop parameters"""
    # Arrange
    player_session = PlayerSession(
        player_id="player123",
        attended=True,
        justified_absence=False,
        motive=None,
        intervals=[
            Interval(datetime(2025, 10, 1, 9, 0, 0), datetime(2025, 10, 1, 12, 0, 0))  # 3 hours
        ]
    )

    # Act
    result = player_session.get_total_time(
        crop_initial=datetime(2025, 10, 1, 10, 0, 0),
        crop_final=datetime(2025, 10, 1, 11, 0, 0)
    )

    # Assert
    assert_that(result, equal_to(3600))  # 1 hour cropped


@pytest.mark.unit
def test_player_session_get_total_time_skips_open_intervals():
    """Test PlayerSession.get_total_time skips open intervals"""
    # Arrange
    player_session = PlayerSession(
        player_id="player123",
        attended=True,
        justified_absence=False,
        motive=None,
        intervals=[
            Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 11, 0, 0)),  # 1 hour
            Interval(datetime(2025, 10, 1, 11, 30, 0), None)  # Open interval
        ]
    )

    # Act
    result = player_session.get_total_time()

    # Assert
    assert_that(result, equal_to(3600))  # Only closed interval


@pytest.mark.unit
def test_player_session_has_attended_true():
    """Test PlayerSession.has_attended returns True when time >= min_time"""
    # Arrange
    player_session = PlayerSession(
        player_id="player123",
        attended=None,
        justified_absence=False,
        motive=None,
        intervals=[
            Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 11, 0, 0))  # 1 hour
        ]
    )

    # Act
    result = player_session.has_attended(min_time=1800)  # 30 minutes

    # Assert
    assert_that(result, is_(True))


@pytest.mark.unit
def test_player_session_has_attended_false():
    """Test PlayerSession.has_attended returns False when time < min_time"""
    # Arrange
    player_session = PlayerSession(
        player_id="player123",
        attended=False,
        justified_absence=False,
        motive=None,
        intervals=[
            Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 10, 15, 0))  # 15 minutes
        ]
    )

    # Act
    result = player_session.has_attended(min_time=1800)  # 30 minutes

    # Assert
    assert_that(result, is_(False))


# ============================================================================
# Session Tests
# ============================================================================

@pytest.mark.unit
def test_session_was_concluded_positively_true():
    """Test Session.was_concluded_positively returns True when COMPLETED"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=datetime(2025, 10, 1, 12, 0, 0),
        type=Type.OFFICIAL_GAME,
        status=Status.COMPLETED,
        players=[]
    )

    # Act
    result = session.was_concluded_positively()

    # Assert
    assert_that(result, is_(True))


@pytest.mark.unit
def test_session_was_concluded_positively_false():
    """Test Session.was_concluded_positively returns False when not COMPLETED"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[]
    )

    # Act
    result = session.was_concluded_positively()

    # Assert
    assert_that(result, is_(False))


@pytest.mark.unit
def test_session_any_player_connected_true():
    """Test Session.any_player_connected returns True when player has open interval"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession(
                player_id="player123",
                attended=None,
                justified_absence=False,
                motive=None,
                intervals=[Interval(datetime(2025, 10, 1, 10, 0, 0), None)]
            )
        ]
    )

    # Act
    result = session.any_player_connected()

    # Assert
    assert_that(result, is_(True))


@pytest.mark.unit
def test_session_any_player_connected_false():
    """Test Session.any_player_connected returns False when all intervals closed"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession(
                player_id="player123",
                attended=None,
                justified_absence=False,
                motive=None,
                intervals=[Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 11, 0, 0))]
            )
        ]
    )

    # Act
    result = session.any_player_connected()

    # Assert
    assert_that(result, is_(False))


@pytest.mark.unit
def test_session_get_player_found():
    """Test Session.get_player returns player when found"""
    # Arrange
    player_session = PlayerSession("player123", None, False, None, [])
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[player_session]
    )

    # Act
    result = session.get_player("player123")

    # Assert
    assert_that(result, equal_to(player_session))


@pytest.mark.unit
def test_session_get_player_not_found():
    """Test Session.get_player returns None when not found"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[]
    )

    # Act
    result = session.get_player("nonexistent")

    # Assert
    assert_that(result, none())


@pytest.mark.unit
def test_session_add_player_new():
    """Test Session.add_player adds new player"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[]
    )

    # Act
    result = session.add_player("player123", attended=False, justified_absence=True, motive="sick")

    # Assert
    assert_that(len(session.players), equal_to(1))
    assert_that(result.player_id, equal_to("player123"))
    assert_that(result.attended, is_(False))
    assert_that(result.justified_absence, is_(True))
    assert_that(result.motive, equal_to("sick"))


@pytest.mark.unit
def test_session_add_player_existing():
    """Test Session.add_player returns existing player if already added"""
    # Arrange
    existing_player = PlayerSession("player123", None, False, None, [])
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[existing_player]
    )

    # Act
    result = session.add_player("player123")

    # Assert
    assert_that(len(session.players), equal_to(1))
    assert_that(result, equal_to(existing_player))


@pytest.mark.unit
def test_session_register_player_connection():
    """Test Session.register_player_connection creates new interval"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[]
    )

    # Act
    session.register_player_connection("player123", datetime(2025, 10, 1, 10, 0, 0))

    # Assert
    assert_that(len(session.players), equal_to(1))
    assert_that(len(session.players[0].intervals), equal_to(1))
    assert_that(session.players[0].intervals[0].start, equal_to(datetime(2025, 10, 1, 10, 0, 0)))
    assert_that(session.version, equal_to(2))  # Incremented


@pytest.mark.unit
def test_session_register_player_connection_closes_previous():
    """Test Session.register_player_connection closes previous open interval"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession(
                "player123",
                None,
                False,
                None,
                [Interval(datetime(2025, 10, 1, 10, 0, 0), None)]
            )
        ]
    )

    # Act
    session.register_player_connection("player123", datetime(2025, 10, 1, 11, 0, 0))

    # Assert
    assert_that(len(session.players[0].intervals), equal_to(2))
    assert_that(session.players[0].intervals[0].end, equal_to(datetime(2025, 10, 1, 11, 0, 0)))


@pytest.mark.unit
def test_session_register_player_disconnection():
    """Test Session.register_player_disconnection closes open interval"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession(
                "player123",
                None,
                False,
                None,
                [Interval(datetime(2025, 10, 1, 10, 0, 0), None)]
            )
        ]
    )

    # Act
    session.register_player_disconnection("player123", datetime(2025, 10, 1, 11, 0, 0))

    # Assert
    assert_that(session.players[0].intervals[0].end, equal_to(datetime(2025, 10, 1, 11, 0, 0)))
    assert_that(session.version, equal_to(2))


@pytest.mark.unit
def test_session_is_concluded_true():
    """Test Session.is_concluded returns True when ended and not DRAFT"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=datetime(2025, 10, 1, 12, 0, 0),
        type=Type.OFFICIAL_GAME,
        status=Status.COMPLETED,
        players=[]
    )

    # Act
    result = session.is_concluded()

    # Assert
    assert_that(result, is_(True))


@pytest.mark.unit
def test_session_is_concluded_false_no_end_time():
    """Test Session.is_concluded returns False when no end_time"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[]
    )

    # Act
    result = session.is_concluded()

    # Assert
    assert_that(result, is_(False))


@pytest.mark.unit
def test_session_get_official_start_time_enough_players():
    """Test Session.get_official_start_time returns third player join time"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession("p1", None, False, None, [Interval(datetime(2025, 10, 1, 10, 0, 0), None)]),
            PlayerSession("p2", None, False, None, [Interval(datetime(2025, 10, 1, 10, 5, 0), None)]),
            PlayerSession("p3", None, False, None, [Interval(datetime(2025, 10, 1, 10, 10, 0), None)])
        ]
    )

    # Act
    result = session.get_official_start_time(min_players=3)

    # Assert
    assert_that(result, equal_to(datetime(2025, 10, 1, 10, 10, 0)))


@pytest.mark.unit
def test_session_get_official_start_time_not_enough_players():
    """Test Session.get_official_start_time returns session start when not enough players"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession("p1", None, False, None, [Interval(datetime(2025, 10, 1, 10, 0, 0), None)])
        ]
    )

    # Act
    result = session.get_official_start_time(min_players=3)

    # Assert
    assert_that(result, equal_to(datetime(2025, 10, 1, 10, 0, 0)))


@pytest.mark.unit
def test_session_get_official_end_time_enough_players():
    """Test Session.get_official_end_time returns third player left time"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=datetime(2025, 10, 1, 10, 15, 0),
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession("p1", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 10, 15, 0))]),
            PlayerSession("p2", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 1, 0), datetime(2025, 10, 1, 10, 5, 0))]),
            PlayerSession("p3", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 2, 0), datetime(2025, 10, 1, 10, 10, 0))]),
        ]
    )

    # Act
    result = session.get_official_end_time(min_players=3)

    # Assert
    # p2 leaves and the number of online players drops below 3 ( the min)
    assert_that(result, equal_to(datetime(2025, 10, 1, 10, 5, 0)))


@pytest.mark.unit
def test_session_get_official_end_time_still_online():
    """Test Session.get_official_end_time but there are players online"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession("p1", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 10, 15, 0))]),
            PlayerSession("p2", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 1, 0), datetime(2025, 10, 1, 10, 5, 0))]),
            PlayerSession("p3", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 2, 0), datetime(2025, 10, 1, 10, 10, 0))]),
            PlayerSession("p4", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 2, 0), None)]),
        ]
    )

    # Act
    result = session.get_official_end_time(min_players=3)

    # Assert
    # p2 leaves and the number of online players drops below 3 ( the min)
    assert_that(result, equal_to(datetime(2025, 10, 1, 10, 5, 0)))


@pytest.mark.unit
def test_session_get_official_end_time_players_online():
    """Test Session.get_official_end_time but almost all players are online"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession("p1", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 10, 15, 0))]),
            PlayerSession("p2", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 1, 0), None)]),
            PlayerSession("p3", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 2, 0), None)]),
            PlayerSession("p4", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 2, 0), None)]),
        ]
    )

    # Act
    result = session.get_official_end_time(min_players=3)

    # Assert
    # p2 leaves and the number of online players drops below 3 ( the min)
    assert_that(result is None)


@pytest.mark.unit
def test_session_conclude_success():
    """Test Session.conclude sets end_time and status"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession("p1", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 12, 0, 0))]),
            PlayerSession("p2", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 12, 0, 0))]),
            PlayerSession("p3", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 12, 0, 0))])
        ]
    )

    # Act
    session.conclude(datetime(2025, 10, 1, 12, 0, 0), min_players=3, min_playtime=1800)

    # Assert
    assert_that(session.end_time, equal_to(datetime(2025, 10, 1, 12, 0, 0)))
    assert_that(session.status, equal_to(Status.COMPLETED))
    assert_that(session.version, equal_to(2))


@pytest.mark.unit
def test_session_conclude_discard():
    """Test Session.conclude sets end_time and status but it is DISCARDED"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession("p1", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 12, 0, 0))]),
            PlayerSession("p2", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 12, 0, 0))]),
            PlayerSession("p3", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 12, 0, 0))])
        ]
    )

    # Act
    session.conclude(datetime(2025, 10, 1, 12, 0, 0), min_players=3, min_playtime=18000)

    # Assert
    assert_that(session.end_time, equal_to(datetime(2025, 10, 1, 12, 0, 0)))
    assert_that(session.status, equal_to(Status.DISCARDED))
    assert_that(session.version, equal_to(2))


@pytest.mark.unit
def test_session_conclude_already_concluded():
    """Test Session.conclude raises exception when already concluded"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=datetime(2025, 10, 1, 12, 0, 0),
        type=Type.OFFICIAL_GAME,
        status=Status.COMPLETED,
        players=[]
    )

    # Act & Assert
    with pytest.raises(SessionAlreadyConcludedException):
        session.conclude(datetime(2025, 10, 1, 13, 0, 0))


@pytest.mark.unit
def test_session_conclude_cannot_conclude():
    """Test Session.conclude raises exception when players still connected"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession("p1", False, False, None, [Interval(datetime(2025, 10, 1, 10, 0, 0), None)])
        ]
    )

    # Act & Assert
    with pytest.raises(CannotConcludeSessionException):
        session.conclude(datetime(2025, 10, 1, 12, 0, 0))


@pytest.mark.unit
def test_session_can_conclude_true():
    """Test Session.can_conclude returns True when no players connected"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession("p1", False, False, None,
                          [Interval(datetime(2025, 10, 1, 10, 0, 0), datetime(2025, 10, 1, 11, 0, 0))])
        ]
    )

    # Act
    result = session.can_conclude()

    # Assert
    assert_that(result, is_(True))


@pytest.mark.unit
def test_session_can_conclude_false():
    """Test Session.can_conclude returns False when players connected"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[
            PlayerSession("p1", False, False, None, [Interval(datetime(2025, 10, 1, 10, 0, 0), None)])
        ]
    )

    # Act
    result = session.can_conclude()

    # Assert
    assert_that(result, is_(False))


@pytest.mark.unit
def test_session_increment_version():
    """Test Session.increment_version increments version by 1"""
    # Arrange
    session = Session(
        id="session123",
        season_id="season456",
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[],
        version=5
    )

    # Act
    session.increment_version()

    # Assert
    assert_that(session.version, equal_to(6))
