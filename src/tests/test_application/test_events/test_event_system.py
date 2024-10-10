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


def set_up(listener=None):
    event_system = EventSystem()
    event = Event(EventType.MEMBER_JOINED_CHANNEL)
    if listener:
        event.listeners.append(listener)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = event
    event_system.event_queue = MagicMock()
    return event_system


def test_emit_event_ok():
    # Given
    event_system = set_up()
    pururu_event = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    # When
    event_system.emit_event(pururu_event)
    # Then
    event_system.event_queue.put_nowait.assert_called_once_with(pururu_event)


def test_emit_event_ko():
    # Given
    event_system = EventSystem()
    pururu_event = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    # When-Then
    assert_that(calling(event_system.emit_event)
                .with_args(pururu_event), raises(ValueError))


def test_emit_event_with_delay_ok():
    # Given
    event_system = set_up()
    pururu_event = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    # When-Then
    with patch.object(event_system, 'emit_event') as mock_emit_event:
        event_system.events[EventType.MEMBER_JOINED_CHANNEL] = Event(EventType.MEMBER_JOINED_CHANNEL)
        event_system.emit_event_with_delay(pururu_event, 0)
        mock_emit_event.assert_called_once_with(pururu_event)


@pytest.mark.asyncio
async def test_emit_event_processing_sync_listener():
    # Given
    listener = MagicMock()
    event_system = EventSystem()
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = Event(EventType.MEMBER_JOINED_CHANNEL)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL].listeners.append(listener)
    event = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    await event_system.event_queue.put(event)
    # When
    asyncio.create_task(event_system.start_event_processing())
    await asyncio.sleep(0.1)
    event_system.stop_event_processing()
    # Then
    listener.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_emit_event_processing_async_listener():
    # Given
    listener = AsyncMock()
    event_system = EventSystem()
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = Event(EventType.MEMBER_JOINED_CHANNEL)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL].listeners.append(listener)
    event = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    await event_system.event_queue.put(event)
    # When
    asyncio.create_task(event_system.start_event_processing())
    await asyncio.sleep(0.5)
    event_system.stop_event_processing()
    # Then
    listener.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_events_processing_concurrency():
    # Given
    call_count = 0

    async def listener(_):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.2)

    event_system = EventSystem()
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = Event(EventType.MEMBER_JOINED_CHANNEL)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL].listeners.append(listener)
    event = Mock(event_type=EventType.MEMBER_JOINED_CHANNEL)
    await event_system.event_queue.put(event)
    await event_system.event_queue.put(event)
    # When
    asyncio.create_task(event_system.start_event_processing())
    await asyncio.sleep(0.1)
    event_system.stop_event_processing()
    # Then
    assert_that(call_count, equal_to(1))
