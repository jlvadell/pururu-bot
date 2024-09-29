import os
import threading
import time

from pururu.application.events.entities import PururuEvent, EventType

from pururu import config

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
        self.last_emitted = None

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

    def emit_event(self, event_name: EventType, data) -> None:
        now :time = time.time()
        if self.last_emitted and self.last_emitted > now - config.EVENT_CONCURRENCY_TIME:
            self.emit_event_with_delay(event_name, data, config.EVENT_DELAY_TIME)
            self.last_emitted = time.time()
        elif  event_name in self.events:
            self.events[event_name].notify_listeners(data)
            self.last_emitted = time.time()
        else:
            raise ValueError(f"Event {event.event_type} does not exist.")

    def emit_event_with_delay(self, event: PururuEvent, delay_seconds) -> None:
        def delayed_emit():
            self.emit_event(event)

        timer = threading.Timer(delay_seconds, delayed_emit)
        timer.start()
