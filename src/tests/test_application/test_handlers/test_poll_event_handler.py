from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from hamcrest import assert_that, instance_of, equal_to

from pururu.application.handlers.poll_event_handler import PollEventHandler
from pururu.domain.messaging.events.secondary_events import CheckExpiredPollsEvent, FinalizePollEvent
from pururu.domain.services.poll_system.poll_system_service import PollSystemService


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBus for testing"""
    return MagicMock()


@pytest.fixture
def mock_poll_system_service():
    """Create a mock PollSystemService for testing"""
    mock = AsyncMock(spec=PollSystemService)
    # Ensure synchronous methods are also properly mocked
    mock.__class__ = type('AsyncMockPollService', (AsyncMock, MagicMock), {})
    return mock


@pytest.fixture
def handler(mock_event_bus, mock_poll_system_service):
    """Create a PollEventHandler instance with mocked dependencies"""
    return PollEventHandler(mock_event_bus, mock_poll_system_service)


@pytest.mark.unit
def test_subscribe_events(handler, mock_event_bus):
    """Test that events are subscribed correctly"""
    # Arrange
    expected_calls = [
        ((CheckExpiredPollsEvent.event_type, handler.handle_check_expired_polls_event),),
        ((FinalizePollEvent.event_type, handler.handle_finalize_poll_event),)
    ]

    # Assert
    assert_that(mock_event_bus.subscribe.call_count, equal_to(len(expected_calls)))
    mock_event_bus.subscribe.assert_has_calls(expected_calls, any_order=True)


@pytest.mark.unit
@patch('pururu.application.handlers.poll_event_handler.datetime')
def test_handle_check_expired_polls_event_with_expired_polls(mock_datetime, handler, mock_event_bus,
                                                             mock_poll_system_service):
    """Test handle_check_expired_polls_event with expired polls"""
    # Arrange
    fixed_time = datetime(2025, 10, 1, 12, 0, 0)
    mock_datetime.now.return_value = fixed_time

    mock_poll1 = MagicMock()
    mock_poll1.id = "poll1"
    mock_poll2 = MagicMock()
    mock_poll2.id = "poll2"
    mock_poll_system_service.get_expired_polls.return_value = [mock_poll1, mock_poll2]

    event = CheckExpiredPollsEvent(fixed_time)

    # Act
    handler.handle_check_expired_polls_event(event)

    # Assert
    mock_poll_system_service.get_expired_polls.assert_called_once()
    assert_that(mock_event_bus.publish.call_count, equal_to(2))

    # Verify FinalizePollEvent published for each poll
    first_event = mock_event_bus.publish.call_args_list[0][0][0]
    second_event = mock_event_bus.publish.call_args_list[1][0][0]
    assert_that(first_event, instance_of(FinalizePollEvent))
    assert_that(second_event, instance_of(FinalizePollEvent))


@pytest.mark.unit
def test_handle_check_expired_polls_event_with_no_expired_polls(handler, mock_event_bus, mock_poll_system_service):
    """Test handle_check_expired_polls_event with no expired polls"""
    # Arrange
    mock_poll_system_service.get_expired_polls.return_value = []
    event = CheckExpiredPollsEvent(datetime.now())

    # Act
    handler.handle_check_expired_polls_event(event)

    # Assert
    mock_poll_system_service.get_expired_polls.assert_called_once()
    mock_event_bus.publish.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_finalize_poll_event(handler, mock_poll_system_service):
    """Test handle_finalize_poll_event"""
    # Arrange
    event = FinalizePollEvent(datetime.now(), "poll123")

    # Act
    await handler.handle_finalize_poll_event(event)

    # Assert
    mock_poll_system_service.finalize_poll.assert_called_once_with("poll123")
