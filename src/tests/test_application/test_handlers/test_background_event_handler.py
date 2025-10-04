from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, instance_of

from pururu.application.handlers.background_event_handler import BackgroundEventHandler
from pururu.domain.messaging.events.secondary_events import CheckExpiredPollsEvent


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBus for testing"""
    return MagicMock()


@pytest.fixture
def handler(mock_event_bus):
    """Create a BackgroundEventHandler instance with mocked dependencies"""
    return BackgroundEventHandler(mock_event_bus)


# Test trigger_check_expired_polls_flow
@pytest.mark.unit
@patch('pururu.application.handlers.background_event_handler.datetime')
def test_trigger_check_expired_polls_flow_publishes_event(mock_datetime, handler, mock_event_bus):
    """Test that trigger_check_expired_polls_flow publishes a CheckExpiredPollsEvent"""
    # Arrange
    fixed_time = datetime(2025, 10, 1, 12, 0, 0)
    mock_datetime.now.return_value = fixed_time

    # Act
    handler.trigger_check_expired_polls_flow()

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert_that(published_event, instance_of(CheckExpiredPollsEvent))
    assert_that(published_event.created_at, instance_of(datetime))


# Test on_configuration_files_changed
@pytest.mark.unit
@patch('pururu.application.handlers.background_event_handler.logger')
@patch('pururu.application.handlers.background_event_handler.settings')
def test_on_configuration_files_changed_reloads_settings(mock_settings, mock_logger_module, handler):
    """Test that on_configuration_files_changed reloads settings"""
    # Act
    handler.on_configuration_files_changed()

    # Assert
    mock_settings.reload.assert_called_once()


@pytest.mark.unit
@patch('pururu.application.handlers.background_event_handler.logger')
@patch('pururu.application.handlers.background_event_handler.settings')
def test_on_configuration_files_changed_resets_logging(mock_settings, mock_logger_module, handler):
    """Test that on_configuration_files_changed resets logging"""
    # Act
    handler.on_configuration_files_changed()

    # Assert
    mock_logger_module.reset_logging.assert_called_once()
