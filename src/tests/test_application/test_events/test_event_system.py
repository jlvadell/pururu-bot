import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock

import pytest
from hamcrest import assert_that, is_in, raises, calling, equal_to

from pururu.application.events.entities import EventType
from pururu.application.events.event_system import Event, EventSystem


def listener_example(*args):
    # Test listener function
    pass


def test_register_listener_ok():
    # Given
    event_system = EventSystem()
    event = Event(EventType.MEMBER_JOINED_CHANNEL)
    event_system.create_event(EventType.MEMBER_JOINED_CHANNEL)
    # When
    event_system.register_listener(EventType.MEMBER_JOINED_CHANNEL, listener_example)
    # Then
    assert_that(event.name, is_in(event_system.events.keys()))
    assert_that(listener_example, is_in(event_system.events[EventType.MEMBER_JOINED_CHANNEL].listeners))


def test_register_listener_ko():
    # Given
    event_system = EventSystem()
    # When-Then
    assert_that(calling(event_system.register_listener)
                .with_args(EventType.MEMBER_JOINED_CHANNEL, listener_example), raises(ValueError))


def test_unregister_listener_ok():
    # Given
    event_system = EventSystem()
    event = Event(EventType.MEMBER_JOINED_CHANNEL)
    event.listeners.append(listener_example)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = event
    # When
    event_system.unregister_listener(EventType.MEMBER_JOINED_CHANNEL, listener_example)
    # Then
    assert_that(event.name, is_in(event_system.events.keys()))
    assert_that(event_system.events[EventType.MEMBER_JOINED_CHANNEL].listeners, equal_to([]))


def test_unregister_listener_ko():
    # Given
    event_system = EventSystem()
    # When-Then
    assert_that(calling(event_system.unregister_listener)
                .with_args(EventType.MEMBER_JOINED_CHANNEL, listener_example), raises(ValueError))


def test_emit_event_ok():
    # Given
    event_system = EventSystem()
    event = Event(EventType.MEMBER_JOINED_CHANNEL)
    listener_mock = Mock()
    event.listeners.append(listener_mock)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = event
    pururu_event = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    # When
    event_system.emit_event(pururu_event)
    # Then
    listener_mock.assert_called_once_with(pururu_event)


@patch('time.time', MagicMock(return_value=100))
@patch('threading.Timer')
def test_emit_event_when_concurrent_events_should_delay(timer_mock):
    # Given
    event_system = EventSystem()
    event = Event(EventType.MEMBER_JOINED_CHANNEL)
    listener_mock = Mock()
    event.listeners.append(listener_mock)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = event
    pururu_event_1 = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    pururu_event_2 = Mock(event_type=EventType.MEMBER_LEFT_CHANNEL)
    # When
    event_system.emit_event(pururu_event_1)
    event_system.emit_event(pururu_event_2)
    # Then
    listener_mock.assert_called_once_with(pururu_event_1)
    timer_mock.assert_called_once()


def test_emit_event_ko():
    # Given
    event_system = EventSystem()
    pururu_event = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    # When-Then
    assert_that(calling(event_system.emit_event)
                .with_args(pururu_event), raises(ValueError))


def test_emit_event_with_delay_ok():
    # Given
    event_system = EventSystem()
    pururu_event = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    # When-Then
    with patch.object(event_system, 'emit_event') as mock_emit_event:
        event_system.events[EventType.MEMBER_JOINED_CHANNEL] = Event(EventType.MEMBER_JOINED_CHANNEL)
        event_system.emit_event_with_delay(pururu_event, 0)
        mock_emit_event.assert_called_once_with(pururu_event)


def test_emit_event_with_async_listener_ok():
    # Given
    event_system = EventSystem()
    event = Event(EventType.MEMBER_JOINED_CHANNEL)
    listener_mock = AsyncMock()
    event.listeners.append(listener_mock)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = event
    pururu_event = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    # When
    event_system.emit_event(pururu_event)
    # Then
    listener_mock.assert_called_once_with(pururu_event)

@pytest.mark.asyncio
async def test_emit_event_with_async_listener_asyncio_loop_running():
    # Given
    event_system = EventSystem()
    event = Event(EventType.MEMBER_JOINED_CHANNEL)
    listener_mock = AsyncMock()
    event.listeners.append(listener_mock)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = event
    pururu_event = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    await asyncio.sleep(1)
    # When
    event_system.emit_event(pururu_event)
    # Then
    listener_mock.assert_called_once_with(pururu_event)
