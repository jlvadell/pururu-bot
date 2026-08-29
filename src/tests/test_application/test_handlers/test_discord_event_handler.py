from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, instance_of, equal_to, none

from pururu.application.handlers.discord_event_handler import DiscordEventHandler
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import (PlayerJoinedSessionEvent, PlayerLeftSessionEvent,
                                                           SessionTypeChangeEvent, SessionAttendanceEditEvent,
                                                           SessionAttendanceRepairEvent, PlayerGameDetectedEvent,
                                                           SessionGameEditEvent)
from pururu.domain.services.session_service import SessionService


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBus for testing"""
    return MagicMock(spec=EventBus)


@pytest.fixture
def mock_session_service():
    """Create a mock SessionService for testing"""
    return MagicMock(spec=SessionService)


@pytest.fixture
def handler(mock_event_bus, mock_session_service):
    """Create a DiscordEventHandler instance with mocked dependencies"""
    return DiscordEventHandler(mock_event_bus, mock_session_service)


# Test handle_on_voice_state_update_event
@pytest.mark.unit
@patch('pururu.application.handlers.discord_event_handler.settings')
@patch('pururu.application.handlers.discord_event_handler.datetime')
def test_handle_voice_state_update_player_joined(mock_datetime, mock_settings, handler, mock_event_bus):
    # Arrange
    mock_settings.general.players.keys.return_value = ["123", "456"]
    fixed_time = datetime(2025, 10, 1, 12, 0, 0)
    mock_datetime.now.return_value = fixed_time

    # Act
    handler.handle_on_voice_state_update_event("123", "player1", None, "voice-channel")

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(PlayerJoinedSessionEvent))


@pytest.mark.unit
@patch('pururu.application.handlers.discord_event_handler.settings')
@patch('pururu.application.handlers.discord_event_handler.datetime')
def test_handle_voice_state_update_player_left(mock_datetime, mock_settings, handler, mock_event_bus):
    # Arrange
    mock_settings.general.players.keys.return_value = ["123", "456"]
    fixed_time = datetime(2025, 10, 1, 12, 0, 0)
    mock_datetime.now.return_value = fixed_time

    # Act
    handler.handle_on_voice_state_update_event("123", "player1", "voice-channel", None)

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(PlayerLeftSessionEvent))


@pytest.mark.unit
@patch('pururu.application.handlers.discord_event_handler.settings')
def test_handle_voice_state_update_channel_switch_ignored(mock_settings, handler, mock_event_bus):
    # Arrange
    mock_settings.general.players.keys.return_value = ["player1", "player2"]

    # Act
    handler.handle_on_voice_state_update_event("123", "player1", "channel1", "channel2")

    # Assert
    mock_event_bus.publish.assert_not_called()


@pytest.mark.unit
@patch('pururu.application.handlers.discord_event_handler.settings')
def test_handle_voice_state_update_non_tracked_player(mock_settings, handler, mock_event_bus):
    # Arrange
    mock_settings.general.players.keys.return_value = ["player1", "player2"]

    # Act
    handler.handle_on_voice_state_update_event("123", "unknown_player", None, "voice-channel")

    # Assert
    mock_event_bus.publish.assert_not_called()


@pytest.mark.unit
def test_handle_on_ready_event(handler):
    # Act & Assert
    handler.handle_on_ready_event()  # Just ensure it runs without error


@pytest.mark.unit
def test_handle_change_type_command_found(handler, mock_session_service):
    # Arrange
    session_id = "session123"
    mock_session = MagicMock()
    mock_session_service.find_session_by_id.return_value = mock_session

    # Act
    result = handler.handle_change_type_command(session_id)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with(session_id)
    assert_that(result, equal_to(mock_session))


@pytest.mark.unit
def test_handle_change_type_command_not_found(handler, mock_session_service):
    # Arrange
    session_id = "session123"
    mock_session_service.find_session_by_id.return_value = None

    # Act
    result = handler.handle_change_type_command(session_id)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with(session_id)
    assert_that(result, none())


@pytest.mark.unit
def test_handle_edit_attendance_command_found(handler, mock_session_service):
    # Arrange
    session_id = "session123"
    mock_session = MagicMock()
    mock_session_service.find_session_by_id.return_value = mock_session

    # Act
    result = handler.handle_edit_attendance_command(session_id)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with(session_id)
    assert_that(result, equal_to(mock_session))


@pytest.mark.unit
def test_handle_edit_attendance_command_not_found(handler, mock_session_service):
    # Arrange
    session_id = "session123"
    mock_session_service.find_session_by_id.return_value = None

    # Act
    result = handler.handle_edit_attendance_command(session_id)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with(session_id)
    assert_that(result, none())


@pytest.mark.unit
def test_handle_repair_attendance_command_found(handler, mock_session_service):
    session = MagicMock()
    mock_session_service.find_session_by_id.return_value = session

    result = handler.handle_repair_attendance_command("session123")

    mock_session_service.find_session_by_id.assert_called_once_with("session123")
    assert_that(result, equal_to(session))


@pytest.mark.unit
def test_handle_repair_attendance_command_not_found(handler, mock_session_service):
    mock_session_service.find_session_by_id.return_value = None

    result = handler.handle_repair_attendance_command("session123")

    mock_session_service.find_session_by_id.assert_called_once_with("session123")
    assert_that(result, none())


@pytest.mark.unit
def test_handle_session_type_change_modal_submit(handler, mock_event_bus):
    # Arrange
    session_type = "someType"
    session_id = "session123"

    # Act
    handler.handle_session_type_change_modal_submit(session_id, session_type)

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(SessionTypeChangeEvent))
    assert_that(published_event.session_id, equal_to(session_id))
    assert_that(published_event.new_type, equal_to(session_type))


@pytest.mark.unit
def test_handle_session_attendance_edit_modal_submit(handler, mock_event_bus):
    # Arrange
    session_id = "session123"
    justifications = {"player1": True, "player2": False}
    motives = {"player1": "Sick", "player2": ""}

    # Act
    handler.handle_session_attendance_edit_modal_submit(session_id, justifications, motives)

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(SessionAttendanceEditEvent))
    assert_that(published_event.session_id, equal_to(session_id))
    assert_that(published_event.justified_absences, equal_to(justifications))
    assert_that(published_event.motives, equal_to(motives))


@pytest.mark.unit
def test_handle_session_attendance_repair_modal_submit(handler, mock_event_bus):
    handler.handle_session_attendance_repair_modal_submit("session123", ["player1", "player2"])

    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(SessionAttendanceRepairEvent))
    assert_that(published_event.session_id, equal_to("session123"))
    assert_that(published_event.player_ids, equal_to(["player1", "player2"]))


@pytest.mark.unit
@patch('pururu.application.handlers.discord_event_handler.settings')
def test_handle_player_game_activity_event_tracked(mock_settings, handler, mock_event_bus):
    mock_settings.general.players.keys.return_value = ["123", "456"]

    handler.handle_player_game_activity_event("123", "player1", "League of Legends")

    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(PlayerGameDetectedEvent))
    assert_that(published_event.player_id, equal_to("123"))
    assert_that(published_event.game_name, equal_to("League of Legends"))


@pytest.mark.unit
@patch('pururu.application.handlers.discord_event_handler.settings')
def test_handle_player_game_activity_event_untracked(mock_settings, handler, mock_event_bus):
    mock_settings.general.players.keys.return_value = ["123"]

    handler.handle_player_game_activity_event("999", "unknown", "League of Legends")

    mock_event_bus.publish.assert_not_called()


@pytest.mark.unit
def test_handle_session_game_edit_modal_submit(handler, mock_event_bus):
    handler.handle_session_game_edit_modal_submit("session123", "Minecraft")

    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(SessionGameEditEvent))
    assert_that(published_event.session_id, equal_to("session123"))
    assert_that(published_event.game_name, equal_to("Minecraft"))
