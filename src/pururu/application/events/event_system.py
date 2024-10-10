import asyncio
import inspect
import threading

import pururu.utils as utils
from pururu.application.events.entities import PururuEvent, EventType


class Event:
    def __init__(self, name: EventType):
        self.name = name
        self.listeners = []

    def register_listener(self, listener) -> None:
        """
        Register a listener for the event
        :param listener: function or coroutine
        :return: None
        """
        if listener not in self.listeners:
            self.listeners.append(listener)

    def unregister_listener(self, listener) -> None:
        """
        Unregister a listener for the event
        :param listener: previously registered listener
        :return: None
        """
        if listener in self.listeners:
            self.listeners.remove(listener)

    async def notify_listeners(self, data: PururuEvent) -> None:
        """
        Notify all listeners for the event
        :param data: PururuEvent
        :return: None
        """
        for listener in self.listeners:
            if inspect.iscoroutinefunction(listener):
                await listener(data)
            else:
                listener(data)


class EventSystem:
    def __init__(self):
        self.events = {}
        self.event_queue = asyncio.Queue()
        self.running = False
        self.logger = utils.get_logger(__name__)

    def create_event(self, event_name: EventType) -> None:
        """
        Adds a new event_type to the event system
        :param event_name: event_type
        :return: None
        """
        if event_name not in self.events:
            self.events[event_name] = Event(event_name)

    def register_listener(self, event_name: EventType, listener) -> None:
        """
        Register a listener for a given event type
        :param event_name: event_type
        :param listener: function or coroutine
        :return: None
        :raises ValueError: if the event_type is not registered; call create_event
        """
        if event_name in self.events:
            self.events[event_name].register_listener(listener)
        else:
            raise ValueError(f"Event {event_name} does not exist.")

    def unregister_listener(self, event_name: EventType, listener) -> None:
        """
        Unregister a listener for a given event type
        :param event_name: event_type
        :param listener: previously registered listener
        :return: None
        :raises ValueError: if the event_type is not registered; call create_event
        """
        if event_name in self.events:
            self.events[event_name].unregister_listener(listener)
        else:
            raise ValueError(f"Event {event_name} does not exist.")

    def emit_event(self, event: PururuEvent) -> None:
        """
        Adds an event to the event queue
        :param event: PururuEvent
        :return: None
        :raises ValueError: if the event_type is not registered; call create_event
        """
        if event.event_type in self.events:
            self.event_queue.put_nowait(event)  # Add event to the queue
        else:
            raise ValueError(f"Event {event.event_type} does not exist.")

    def emit_event_with_delay(self, event: PururuEvent, delay_seconds) -> None:
        def delayed_emit():
            self.emit_event(event)

        timer = threading.Timer(delay_seconds, delayed_emit)
        timer.start()

    async def start_event_processing(self) -> None:
        """
        Start the background event processing
        :return: None
        """
        self.logger.debug("Event processing started")
        self.running = True
        while self.running:
            try:
                event = await self.event_queue.get()  # Wait for event from async queue
                await self._process_event(event)  # Process the event
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")

    def stop_event_processing(self) -> None:
        """
        Stop the background event processing
        :return: None
        """
        self.logger.debug("Event processing stopped")
        self.running = False

    async def _process_event(self, event: PururuEvent) -> None:
        """
        Process an event from the queue
        :param event: PururuEvent
        :return: None
        :raises ValueError: if the event_type is not registered; call create_event
        """
        if event.event_type in self.events:
            await self.events[event.event_type].notify_listeners(event)
        else:
            raise ValueError(f"Event {event.event_type} does not exist.")
