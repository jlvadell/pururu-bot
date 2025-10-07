from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, equal_to, instance_of

from pururu.domain.entities.session import Session, Status, Type, PlayerSession
from pururu.domain.exceptions import (
    SessionNotFoundException,
    SessionAlreadyConcludedException,
    CannotConcludeSessionException
)
from pururu.domain.messaging.events.session_events import (
    SessionConcludeRequestedEvent,
    SessionConcludedEvent,
    SessionTypeChangedEvent,
    SessionAttendanceEditedEvent
)
from pururu.domain.services.session_service import SessionService
from tests.test_domain.conftest import session, season, player


@pytest.fixture
def mock_session_repository():
    """Create a mock SessionRepository"""
    return MagicMock()


@pytest.fixture
def mock_season_service():
    """Create a mock SeasonService"""
    return MagicMock()


@pytest.fixture
def mock_player_service():
    """Create a mock PlayerService"""
    return MagicMock()


@pytest.fixture
def mock_id_generator():
    """Create a mock IdGeneratorService"""
    mock = MagicMock()
    mock.next_id.return_value = "new_session_id"
    return mock


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBus"""
    return MagicMock()


@pytest.fixture
def service(mock_session_repository, mock_season_service, mock_player_service, mock_id_generator, mock_event_bus):
    """Create a SessionService instance"""
    return SessionService(
        mock_session_repository,
        mock_season_service,
        mock_player_service,
        mock_id_generator,
        mock_event_bus
    )


# ============================================================================
# register_player_connection Tests
# ============================================================================

@pytest.mark.unit
def test_register_player_connection_with_active_session(service, mock_session_repository, session):
    """Test register_player_connection updates existing active session"""
    # Arrange
    mock_session_repository.find_active_session.return_value = session
    connection_time = datetime(2025, 10, 1, 10, 30, 0)

    # Act
    service.register_player_connection("player123", connection_time)

    # Assert
    mock_session_repository.find_active_session.assert_called_once()
    mock_session_repository.update.assert_called_once_with(session)


@pytest.mark.unit
def test_register_player_connection_creates_new_session(
        service, mock_session_repository, mock_season_service, mock_player_service, season, player
):
    """Test register_player_connection creates new session when none active"""
    # Arrange
    mock_session_repository.find_active_session.return_value = None
    mock_season_service.get_current_season.return_value = season
    mock_player_service.get_players.return_value = [player]

    new_session = Session(
        id="new_session_id",
        season_id=season.id,
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=[],
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=None
    )
    mock_session_repository.save.return_value = new_session
    connection_time = datetime(2025, 10, 1, 10, 0, 0)

    # Act
    service.register_player_connection("player123", connection_time)

    # Assert
    mock_session_repository.find_active_session.assert_called_once()
    mock_session_repository.save.assert_called_once()


# ============================================================================
# register_player_disconnection Tests
# ============================================================================

@pytest.mark.unit
def test_register_player_disconnection_with_active_session(service, mock_session_repository, session):
    """Test register_player_disconnection updates session"""
    # Arrange
    session.any_player_connected = MagicMock(return_value=True)
    mock_session_repository.find_active_session.return_value = session
    mock_session_repository.update.return_value = session
    disconnection_time = datetime(2025, 10, 1, 12, 0, 0)

    # Act
    service.register_player_disconnection("player123", disconnection_time)

    # Assert
    mock_session_repository.find_active_session.assert_called_once()
    mock_session_repository.update.assert_called_once_with(session)


@pytest.mark.unit
@patch('pururu.domain.services.session_service.datetime')
def test_register_player_disconnection_publishes_conclude_event(
        mock_datetime, service, mock_session_repository, mock_event_bus, session
):
    """Test register_player_disconnection publishes conclude event when no players connected"""
    # Arrange
    fixed_time = datetime(2025, 10, 1, 12, 0, 0)
    mock_datetime.now.return_value = fixed_time
    session.any_player_connected = MagicMock(return_value=False)
    mock_session_repository.find_active_session.return_value = session
    mock_session_repository.update.return_value = session
    disconnection_time = datetime(2025, 10, 1, 12, 0, 0)

    # Act
    service.register_player_disconnection("player123", disconnection_time)

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(SessionConcludeRequestedEvent))
    assert_that(published_event.session_id, equal_to(session.id))


@pytest.mark.unit
def test_register_player_disconnection_no_active_session(service, mock_session_repository):
    """Test register_player_disconnection returns early when no active session"""
    # Arrange
    mock_session_repository.find_active_session.return_value = None
    disconnection_time = datetime(2025, 10, 1, 12, 0, 0)

    # Act
    service.register_player_disconnection("player123", disconnection_time)

    # Assert
    mock_session_repository.find_active_session.assert_called_once()
    mock_session_repository.update.assert_not_called()


# ============================================================================
# conclude_session Tests
# ============================================================================

@pytest.mark.unit
@patch('pururu.domain.services.session_service.datetime')
@patch('pururu.domain.services.session_service.settings')
def test_conclude_session_success(mock_settings, mock_datetime, service, mock_session_repository, mock_event_bus,
                                  session):
    """Test conclude_session successfully concludes session"""
    # Arrange
    fixed_time = datetime(2025, 10, 1, 12, 0, 0)
    mock_datetime.now.return_value = fixed_time
    mock_settings.general.min_attendance_members = 2
    mock_settings.general.min_attendance_time = 300
    mock_session_repository.find_by_id.return_value = session
    end_time = datetime(2025, 10, 1, 12, 0, 0)

    # Act
    service.conclude_session("session123", end_time)

    # Assert
    mock_session_repository.find_by_id.assert_called_once_with("session123")
    mock_session_repository.update.assert_called_once_with(session)
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(SessionConcludedEvent))


@pytest.mark.unit
def test_conclude_session_not_found(service, mock_session_repository):
    """Test conclude_session raises SessionNotFoundException when session not found"""
    # Arrange
    mock_session_repository.find_by_id.return_value = None
    end_time = datetime(2025, 10, 1, 12, 0, 0)

    # Act & Assert
    with pytest.raises(SessionNotFoundException):
        service.conclude_session("nonexistent", end_time)


@pytest.mark.unit
@patch('pururu.domain.services.session_service.settings')
def test_conclude_session_already_concluded(mock_settings, service, mock_session_repository, session):
    """Test conclude_session handles SessionAlreadyConcludedException"""
    # Arrange
    mock_settings.general.min_attendance_members = 2
    mock_settings.general.min_attendance_time = 300
    mock_session_repository.find_by_id.return_value = session
    session.conclude = MagicMock(side_effect=SessionAlreadyConcludedException())
    end_time = datetime(2025, 10, 1, 12, 0, 0)

    # Act
    service.conclude_session("session123", end_time)

    # Assert
    mock_session_repository.update.assert_not_called()


@pytest.mark.unit
@patch('pururu.domain.services.session_service.settings')
def test_conclude_session_cannot_conclude(mock_settings, service, mock_session_repository, session):
    """Test conclude_session handles CannotConcludeSessionException"""
    # Arrange
    mock_settings.general.min_attendance_members = 2
    mock_settings.general.min_attendance_time = 300
    mock_session_repository.find_by_id.return_value = session
    session.conclude = MagicMock(side_effect=CannotConcludeSessionException())
    end_time = datetime(2025, 10, 1, 12, 0, 0)

    # Act
    service.conclude_session("session123", end_time)

    # Assert
    mock_session_repository.update.assert_not_called()


# ============================================================================
# find_session_by_id Tests
# ============================================================================

@pytest.mark.unit
def test_find_session_by_id_returns_session(service, mock_session_repository, session):
    """Test find_session_by_id returns session when found"""
    # Arrange
    mock_session_repository.find_by_id.return_value = session

    # Act
    result = service.find_session_by_id("session123")

    # Assert
    mock_session_repository.find_by_id.assert_called_once_with("session123")
    assert_that(result, equal_to(session))


@pytest.mark.unit
def test_find_session_by_id_raises_not_found(service, mock_session_repository):
    """Test find_session_by_id raises SessionNotFoundException when not found"""
    # Arrange
    mock_session_repository.find_by_id.return_value = None

    # Act & Assert
    with pytest.raises(SessionNotFoundException):
        service.find_session_by_id("nonexistent")


# ============================================================================
# change_session_type
# ============================================================================

@pytest.mark.unit
def test_change_session_type_success(service, mock_session_repository, mock_event_bus, session):
    """Test change_session_type successfully changes session type"""
    # Arrange
    mock_session_repository.find_by_id.return_value = session
    expected = Session(
        id=session.id,
        season_id=session.season_id,
        type=Type.ADDITIONAL_GAME,
        status=session.status,
        players=session.players,
        start_time=session.start_time,
        end_time=session.end_time,
        version=session.version + 1
    )

    # Act
    service.change_session_type(session.id, Type.ADDITIONAL_GAME)

    # Assert
    mock_session_repository.find_by_id.assert_called_once_with(session.id)
    mock_session_repository.update.assert_called_once_with(expected)
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(SessionTypeChangedEvent))


@pytest.mark.unit
def test_change_session_type_same_type(service, mock_session_repository, mock_event_bus, session):
    """Test change_session_type does not update when type is the same"""
    # Arrange
    mock_session_repository.find_by_id.return_value = session

    # Act
    service.change_session_type(session.id, session.type)

    # Assert
    mock_session_repository.find_by_id.assert_called_once_with(session.id)
    mock_session_repository.update.assert_not_called()
    mock_event_bus.assert_not_called()


@pytest.mark.unit
def test_change_session_type_raises_not_found(service, mock_session_repository):
    """Test change_session_type raises SessionNotFoundException when session not found"""
    # Arrange
    mock_session_repository.find_by_id.return_value = None

    # Act & Assert
    with pytest.raises(SessionNotFoundException):
        service.change_session_type("nonexistent", Type.ADDITIONAL_GAME)
    mock_session_repository.update.assert_not_called()


# ============================================================================
# edit_session_attendance
# ============================================================================

@pytest.mark.unit
def test_edit_session_attendance_success(service, mock_session_repository, mock_event_bus, completed_session,
                                         player_session_absent, player_session_justified):
    """Test edit_session_attendance successfully edits attendance"""
    # Arrange
    completed_session.players = [player_session_absent]
    mock_session_repository.find_by_id.return_value = completed_session

    expected = Session(
        id=completed_session.id,
        season_id=completed_session.season_id,
        type=completed_session.type,
        status=completed_session.status,
        players=[player_session_justified],
        start_time=completed_session.start_time,
        end_time=completed_session.end_time,
        version=completed_session.version + 1
    )

    # Act
    service.edit_session_attendance(completed_session.id, [player_session_justified])

    # Assert
    mock_session_repository.find_by_id.assert_called_once_with(completed_session.id)
    mock_session_repository.update.assert_called_once_with(expected)
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(SessionAttendanceEditedEvent))


@pytest.mark.unit
def test_edit_session_attendance_edit_specific_fields(service, mock_session_repository, mock_event_bus,
                                                      completed_session,
                                                      player_session_absent, player_session_justified):
    """Test edit_session_attendance does not edit other fields than justified and motive"""
    # Arrange
    completed_session.players = [player_session_absent]
    mock_session_repository.find_by_id.return_value = completed_session

    player_session_updated = PlayerSession(
        player_id=player_session_justified.player_id,
        justified_absence=player_session_justified.justified_absence,
        attended=not player_session_absent.attended,  # This field should not be changed by edit_session_attendance
        motive=player_session_justified.motive,
        intervals=[]  # This field should not be changed by edit_session_attendance
    )

    expected = Session(
        id=completed_session.id,
        season_id=completed_session.season_id,
        type=completed_session.type,
        status=completed_session.status,
        players=[player_session_justified],
        start_time=completed_session.start_time,
        end_time=completed_session.end_time,
        version=completed_session.version + 1
    )

    # Act
    service.edit_session_attendance(completed_session.id, [player_session_updated])

    # Assert
    mock_session_repository.find_by_id.assert_called_once_with(completed_session.id)
    mock_session_repository.update.assert_called_once_with(expected)
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(SessionAttendanceEditedEvent))


@pytest.mark.unit
def test_edit_session_attendance_no_changes(service, mock_session_repository, mock_event_bus, completed_session,
                                            player_session_absent):
    """Test edit_session_attendance does not update when no changes"""
    # Arrange
    completed_session.players = [player_session_absent]
    mock_session_repository.find_by_id.return_value = completed_session

    # Act
    service.edit_session_attendance(completed_session.id, [player_session_absent])

    # Assert
    mock_session_repository.find_by_id.assert_called_once_with(completed_session.id)
    mock_session_repository.update.assert_not_called()
    mock_event_bus.assert_not_called()


@pytest.mark.unit
def test_edit_session_attendance_do_not_change_attended_players(service, mock_session_repository, mock_event_bus,
                                                                completed_session,
                                                                player_session):
    """Test edit_session_attendance does not update when trying to change attended players"""
    # Arrange
    mock_session_repository.find_by_id.return_value = completed_session
    modified_player = PlayerSession(player_session.player_id,
                                    justified_absence=True,
                                    attended=True,
                                    motive="Changed",
                                    intervals=player_session.intervals)

    # Act
    service.edit_session_attendance(completed_session.id, [modified_player])

    # Assert
    mock_session_repository.find_by_id.assert_called_once_with(completed_session.id)
    mock_session_repository.update.assert_not_called()
    mock_event_bus.assert_not_called()


@pytest.mark.unit
def test_edit_session_attendance_raises_not_found(service, mock_session_repository, player_session_absent):
    """Test edit_session_attendance raises SessionNotFoundException when session not found"""
    # Arrange
    mock_session_repository.find_by_id.return_value = None

    # Act & Assert
    with pytest.raises(SessionNotFoundException):
        service.edit_session_attendance("nonexistent", [player_session_absent])
    mock_session_repository.update.assert_not_called()

# ============================================================================
# determine_session_type Tests
# ============================================================================

@pytest.mark.unit
def test_determine_session_type_returns_additional(service, mock_session_repository, completed_session,
                                             player_session_online):
    """Test determine_session_type returns ADDITIONAL_GAME when there was an OFFICIAL GAME this week"""
    # Arrange
    completed_session.type = Type.ADDITIONAL_GAME
    mock_session_repository.find_latest_by_type.return_value = completed_session

    # Act
    result = service._determine_session_type(player_session_online.intervals[0].start)

    # Assert
    mock_session_repository.find_latest_by_type.assert_called_once_with(Type.OFFICIAL_GAME)
    assert_that(result, equal_to(Type.ADDITIONAL_GAME))

@pytest.mark.unit
@pytest.mark.parametrize("start_time,mocked_random,description", [
    (datetime(2025, 10, 2, 15, 0, 0), None, "Thursday at 3 PM - always official"),
    (datetime(2025, 10, 2, 22, 0, 0), None, "Thursday at 10 PM - always official"),
    (datetime(2025, 10, 6, 21, 0, 0), 0.24, "Monday at 9 PM with 24% random - 25% threshold"),
    (datetime(2025, 10, 7, 22, 30, 0), 0.20, "Tuesday at 10:30 PM with 20% random - 25% threshold"),
    (datetime(2025, 10, 1, 21, 0, 0), 0.14, "Wednesday at 9 PM with 14% random - 15% threshold"),
    (datetime(2025, 10, 3, 23, 0, 0), 0.10, "Friday at 11 PM with 10% random - 15% threshold"),
    (datetime(2025, 10, 4, 21, 30, 0), 0.05, "Saturday at 9:30 PM with 5% random - 15% threshold"),
    (datetime(2025, 10, 5, 22, 0, 0), 0.0, "Sunday at 10 PM with 0% random - 15% threshold"),
])
@patch('pururu.domain.services.session_service.random')
def test_infer_session_type_from_start_time_returns_official(
        mock_random, service, start_time, mocked_random, description
):
    """Test _infer_session_type_from_start_time returns OFFICIAL_GAME for various conditions"""
    # Arrange
    if mocked_random is not None:
        mock_random.random.return_value = mocked_random
    
    # Act
    result = service._infer_session_type_from_start_time(start_time)
    
    # Assert
    assert_that(result, equal_to(Type.OFFICIAL_GAME), description)


@pytest.mark.unit
@pytest.mark.parametrize("start_time,mocked_random,description", [
    (datetime(2025, 10, 6, 15, 0, 0), None, "Monday at 3 PM - before 9 PM always additional"),
    (datetime(2025, 10, 7, 20, 59, 0), None, "Tuesday at 8:59 PM - before 9 PM always additional"),
    (datetime(2025, 10, 1, 12, 0, 0), None, "Wednesday at noon - before 9 PM always additional"),
    (datetime(2025, 10, 3, 10, 0, 0), None, "Friday at 10 AM - before 9 PM always additional"),
    (datetime(2025, 10, 4, 18, 0, 0), None, "Saturday at 6 PM - before 9 PM always additional"),
    (datetime(2025, 10, 5, 20, 0, 0), None, "Sunday at 8 PM - before 9 PM always additional"),
    (datetime(2025, 10, 6, 21, 0, 0), 0.25, "Monday at 9 PM with 25% random - above 25% threshold"),
    (datetime(2025, 10, 7, 22, 30, 0), 0.50, "Tuesday at 10:30 PM with 50% random - above 25% threshold"),
    (datetime(2025, 10, 6, 23, 0, 0), 0.99, "Monday at 11 PM with 99% random - above 25% threshold"),
    (datetime(2025, 10, 1, 21, 0, 0), 0.15, "Wednesday at 9 PM with 15% random - above 15% threshold"),
    (datetime(2025, 10, 3, 23, 0, 0), 0.20, "Friday at 11 PM with 20% random - above 15% threshold"),
    (datetime(2025, 10, 4, 21, 30, 0), 0.50, "Saturday at 9:30 PM with 50% random - above 15% threshold"),
    (datetime(2025, 10, 5, 22, 0, 0), 0.99, "Sunday at 10 PM with 99% random - above 15% threshold"),
])
@patch('pururu.domain.services.session_service.random')
def test_infer_session_type_from_start_time_returns_additional(
        mock_random, service, start_time, mocked_random, description
):
    """Test _infer_session_type_from_start_time returns ADDITIONAL_GAME for various conditions"""
    # Arrange
    if mocked_random is not None:
        mock_random.random.return_value = mocked_random
    
    # Act
    result = service._infer_session_type_from_start_time(start_time)
    
    # Assert
    assert_that(result, equal_to(Type.ADDITIONAL_GAME), description)