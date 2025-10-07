from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

import pytest
from hamcrest import assert_that, equal_to

from pururu.application.handlers.session_events_handler import SessionEventsHandler
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import (
    PlayerJoinedSessionEvent,
    PlayerLeftSessionEvent,
    SessionConcludeRequestedEvent,
    SessionConcludedEvent,
    SessionTypeChangedEvent,
    SessionAttendanceEditedEvent
)
from pururu.domain.services.discord_service import DiscordService


@pytest.fixture
def mock_session_service():
    """Create a mock SessionService for testing"""
    return MagicMock()


@pytest.fixture
def mock_data_sync_service():
    """Create a mock DataSyncService for testing"""
    return MagicMock()


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBus for testing"""
    return MagicMock(spec=EventBus)


@pytest.fixture
def mock_discord_service():
    """Create a mock DiscordService for testing"""
    return AsyncMock(spec=DiscordService)


@pytest.fixture
def handler(mock_session_service, mock_data_sync_service, mock_event_bus, mock_discord_service):
    """Create a SessionEventsHandler instance with mocked dependencies"""
    return SessionEventsHandler(mock_session_service, mock_data_sync_service, mock_event_bus, mock_discord_service)


@pytest.mark.unit
def test_subscriptions(handler, mock_event_bus):
    """Test that the handler subscribes to the correct events"""
    # Arrange
    expected_calls = [
        ((PlayerJoinedSessionEvent.event_type, handler.handle_player_joined),),
        ((PlayerLeftSessionEvent.event_type, handler.handle_player_left),),
        ((SessionConcludeRequestedEvent.event_type, handler.handle_session_conclude_requested),),
        ((SessionConcludedEvent.event_type, handler.handle_session_concluded),),
        ((SessionTypeChangedEvent.event_type, handler.handle_session_type_changed),),
        ((SessionAttendanceEditedEvent.event_type, handler.handle_session_attendance_edited),),
    ]
    # Assert
    mock_event_bus.subscribe.assert_has_calls(expected_calls, any_order=True)
    assert_that(mock_event_bus.subscribe.call_count, equal_to(len(expected_calls)))


@pytest.mark.unit
def test_handle_player_joined(handler, mock_session_service):
    """Test handle_player_joined"""
    # Arrange
    event_time = datetime(2025, 10, 1, 12, 0, 0)
    event = PlayerJoinedSessionEvent(datetime.now(), "player123", event_time)

    # Act
    handler.handle_player_joined(event)

    # Assert
    mock_session_service.register_player_connection.assert_called_once_with("player123", event_time)


@pytest.mark.unit
def test_handle_player_left(handler, mock_session_service):
    """Test handle_player_left"""
    # Arrange
    event_time = datetime(2025, 10, 1, 12, 30, 0)
    event = PlayerLeftSessionEvent(datetime.now(), "player123", event_time)

    # Act
    handler.handle_player_left(event)

    # Assert
    mock_session_service.register_player_disconnection.assert_called_once_with("player123", event_time)


@pytest.mark.unit
def test_handle_session_conclude_requested(handler, mock_session_service):
    """Test handle_session_conclude_requested"""
    # Arrange
    end_time = datetime(2025, 10, 1, 15, 0, 0)
    event = SessionConcludeRequestedEvent(datetime.now(), "session123", end_time)

    # Act
    handler.handle_session_conclude_requested(event)

    # Assert
    mock_session_service.conclude_session.assert_called_once_with("session123", end_time)


@pytest.mark.unit
def test_handle_session_concluded_with_positive_conclusion(handler, mock_session_service, mock_data_sync_service):
    """Test handle_session_concluded when the session was concluded positively"""
    # Arrange
    mock_session = MagicMock()
    mock_session.was_concluded_positively.return_value = True
    mock_session_service.find_session_by_id.return_value = mock_session

    event = SessionConcludedEvent(datetime.now(), "session123")

    # Act
    handler.handle_session_concluded(event)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with("session123")
    mock_session.was_concluded_positively.assert_called_once()
    mock_data_sync_service.sync_session.assert_called_once_with(mock_session)


@pytest.mark.unit
def test_handle_session_concluded_with_negative_conclusion(handler, mock_session_service, mock_data_sync_service):
    """Test handle_session_concluded when the session was not concluded positively"""
    # Arrange
    mock_session = MagicMock()
    mock_session.was_concluded_positively.return_value = False
    mock_session_service.find_session_by_id.return_value = mock_session

    event = SessionConcludedEvent(datetime.now(), "session123")

    # Act
    handler.handle_session_concluded(event)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with("session123")
    mock_session.was_concluded_positively.assert_called_once()
    mock_data_sync_service.sync_session.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_session_type_changed(handler, mock_session_service, mock_data_sync_service, mock_discord_service):
    """Test handle_session_type_changed"""
    # Arrange
    mock_session = MagicMock()
    mock_session_service.find_session_by_id.return_value = mock_session

    event = SessionTypeChangedEvent(datetime.now(), "session123", "new_type")

    # Act
    await handler.handle_session_type_changed(event)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with("session123")
    mock_discord_service.update_session_info_view_message.assert_awaited_once()
    mock_data_sync_service.sync_session.assert_called_once_with(mock_session)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_session_attendance_edited(handler, mock_session_service, mock_data_sync_service,
                                                mock_discord_service):
    """Test handle_session_attendance_edited"""
    # Arrange
    mock_session = MagicMock()
    mock_session_service.find_session_by_id.return_value = mock_session

    event = SessionAttendanceEditedEvent(datetime.now(), "session123")

    # Act
    await handler.handle_session_attendance_edited(event)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with("session123")
    mock_discord_service.update_session_info_view_message.assert_awaited_once()
    mock_data_sync_service.sync_session.assert_called_once_with(mock_session)
