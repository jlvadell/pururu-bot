import threading

from pururu.application.events.entities import PururuEvent, EventType


class Event:
    def __init__(self, name: EventType):
        self.name = name
        self.listeners = []

    def register_listener(self, listener) -> None:
        if listener not in self.listeners:
            self.listeners.append(listener)

    def unregister_listener(self, listener) -> None:
        if listener in self.listeners:
            self.listeners.remove(listener)

    def notify_listeners(self, data) -> None:
        for listener in self.listeners:
            listener(data)


class EventSystem:
    def __init__(self):
        self.events = {}

    def create_event(self, event_name: EventType) -> None:
        if event_name not in self.events:
            self.events[event_name] = Event(event_name)

    def register_listener(self, event_name: EventType, listener) -> None:
        if event_name in self.events:
            self.events[event_name].register_listener(listener)
        else:
            raise ValueError(f"Event {event_name} does not exist.")

    def unregister_listener(self, event_name: EventType, listener) -> None:
        if event_name in self.events:
            self.events[event_name].unregister_listener(listener)
        else:
            raise ValueError(f"Event {event_name} does not exist.")

    def emit_event(self, event: PururuEvent) -> None:
        if event.event_type in self.events:
            self.events[event.event_type].notify_listeners(event)
        else:
            raise ValueError(f"Event {event.event_type} does not exist.")

    def emit_event_with_delay(self, event: PururuEvent, delay_seconds) -> None:
        def delayed_emit():
            self.emit_event(event)

        timer = threading.Timer(delay_seconds, delayed_emit)
        timer.start()
