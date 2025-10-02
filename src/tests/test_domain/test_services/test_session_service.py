from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, equal_to, instance_of

from pururu.domain.entities.session import Session, Status, Type
from pururu.domain.exceptions import (
    SessionNotFoundException,
    SessionAlreadyConcludedException,
    CannotConcludeSessionException
)
from pururu.domain.messaging.events.session_events import (
    SessionConcludeRequestedEvent,
    SessionConcludedEvent
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
