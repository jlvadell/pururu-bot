from unittest.mock import Mock, patch

from hamcrest import assert_that, is_in, raises, calling, equal_to

from application.events.event_system import EventType, Event, EventSystem


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

