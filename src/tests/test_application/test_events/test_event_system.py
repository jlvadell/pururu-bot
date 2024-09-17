from unittest.mock import Mock, patch, MagicMock

from hamcrest import assert_that, is_in, raises, calling, equal_to

from pururu.application.events.event_system import EventType, Event, EventSystem


def listener_example(*args):
    # Test listener function
    pass


def test_register_listener_ok():
    event_system = EventSystem()
    event = Event(EventType.MEMBER_JOINED_CHANNEL)
    event_system.create_event(EventType.MEMBER_JOINED_CHANNEL)
    event_system.register_listener(EventType.MEMBER_JOINED_CHANNEL, listener_example)
    assert_that(event.name, is_in(event_system.events.keys()))
    assert_that(listener_example, is_in(event_system.events[EventType.MEMBER_JOINED_CHANNEL].listeners))


def test_register_listener_ko():
    event_system = EventSystem()
    assert_that(calling(event_system.register_listener)
                .with_args(EventType.MEMBER_JOINED_CHANNEL, listener_example), raises(ValueError))


def test_unregister_listener_ok():
    event_system = EventSystem()
    event = Event(EventType.MEMBER_JOINED_CHANNEL)
    event.listeners.append(listener_example)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = event
    event_system.unregister_listener(EventType.MEMBER_JOINED_CHANNEL, listener_example)
    assert_that(event.name, is_in(event_system.events.keys()))
    assert_that(event_system.events[EventType.MEMBER_JOINED_CHANNEL].listeners, equal_to([]))


def test_unregister_listener_ko():
    event_system = EventSystem()
    assert_that(calling(event_system.unregister_listener)
                .with_args(EventType.MEMBER_JOINED_CHANNEL, listener_example), raises(ValueError))


def test_emit_event_ok():
    event_system = EventSystem()
    event = Event(EventType.MEMBER_JOINED_CHANNEL)
    listener_mock = Mock()
    event.listeners.append(listener_mock)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = event
    event_system.emit_event(EventType.MEMBER_JOINED_CHANNEL, {"foo": "bar"})
    listener_mock.assert_called_once_with({"foo": "bar"})

@patch('time.time', MagicMock(return_value=100))
@patch('threading.Timer')
def test_emit_event_when_concurrent_events_should_delay(timer_mock):
    # Given
    event_system = EventSystem()
    event = Event(EventType.MEMBER_JOINED_CHANNEL)
    listener_mock = Mock()
    event.listeners.append(listener_mock)
    event_system.events[EventType.MEMBER_JOINED_CHANNEL] = event
    event_system.EVENT_CONCURRENCY_TIME = 10

    # When
    event_system.emit_event(EventType.MEMBER_JOINED_CHANNEL, {"foo1": "bar1"})
    event_system.emit_event(EventType.MEMBER_JOINED_CHANNEL, {"foo2": "bar2"})

    # Then
    listener_mock.assert_called_once_with({"foo1": "bar1"})
    timer_mock.assert_called_once()

def test_emit_event_ko():
    event_system = EventSystem()
    assert_that(calling(event_system.emit_event)
                .with_args(EventType.MEMBER_JOINED_CHANNEL, {"foo": "bar"}), raises(ValueError))


def test_emit_event_with_delay_ok():
    event_system = EventSystem()
    with patch.object(event_system, 'emit_event') as mock_emit_event:
        event_system.events[EventType.MEMBER_JOINED_CHANNEL] = Event(EventType.MEMBER_JOINED_CHANNEL)
        event_system.emit_event_with_delay(EventType.MEMBER_JOINED_CHANNEL, {"foo": "bar"}, 0)
        mock_emit_event.assert_called_once_with(EventType.MEMBER_JOINED_CHANNEL, {"foo": "bar"})