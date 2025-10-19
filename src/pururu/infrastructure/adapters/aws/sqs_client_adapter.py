import asyncio
import json
import time
from typing import Callable

import aioboto3

from pururu.common import logger, metrics
from pururu.config import settings
from pururu.domain.messaging.events import secondary_events, session_events
from pururu.domain.messaging.events.base_events import DomainEvent
from pururu.infrastructure.exceptions import (SQSDeserializationException, SQSHandlerNotFoundException)


class SQSClientAdapter:
    def __init__(self):
        self.logger = logger.get_logger(__name__)
        self.router = EventRouter()
        self.queue_consumers = []
        self._register_consumers()
        self.tasks: list[asyncio.Task] = []

    def subscribe(self, event_type, handler: Callable[[DomainEvent], None]):
        self.router.register(event_type, handler)

    def _register_consumers(self):
        queue_config = settings.aws.sqs_queues
        for queue_name in queue_config.keys():
            consumer = GenericSQSPoller(
                consumer_name=queue_name,
                region=settings.aws.region,
                queue_url=queue_config[queue_name]["queue_url"],
                polling_time=queue_config[queue_name].get("polling_time", 20),
                endpoint_url=queue_config[queue_name]["endpoint_url"],
                router=self.router
            )
            self.queue_consumers.append(consumer)

    def start_polling(self):
        for consumer in self.queue_consumers:
            task: asyncio.Task = asyncio.create_task(consumer.start_polling())
            self.tasks.append(task)

    def stop_polling(self):
        for task in self.tasks:
            try:
                task.cancel()
            except asyncio.CancelledError:
                self.logger.info("Polling task cancelled successfully.")


class EventRouter:
    EVENT_REGISTRY = {}

    @staticmethod
    def _register_events_from_module(module) -> dict:
        return {
            name: obj for name, obj in module.__dict__.items()
            if isinstance(obj, type) and issubclass(obj, DomainEvent) and obj != DomainEvent
        }

    EVENT_REGISTRY.update(_register_events_from_module(secondary_events))
    EVENT_REGISTRY.update(_register_events_from_module(session_events))

    def __init__(self):
        self._routes = {}

    def register(self, event_type, handler):
        self._routes[event_type] = handler

    async def route(self, event):
        handler = self._routes.get(event.event_type)
        if handler:
            return await handler(event) if asyncio.iscoroutinefunction(handler) else handler(event)
        else:
            raise SQSHandlerNotFoundException(f"No handler registered for event type: {event.event_type}")


class GenericSQSPoller:
    def __init__(self, consumer_name: str, region: str, queue_url: str, polling_time: int, endpoint_url: str,
                 router: EventRouter):
        self.consumer_name = consumer_name
        self.logger = logger.get_logger(consumer_name)
        self.aws_session = aioboto3.Session(region_name=region)
        self.queue_url = queue_url
        self.polling_time = polling_time
        self.endpoint_url = endpoint_url
        self.sqs = None
        self.run_polling = False
        self.router = router

    def _deserialize_event(self, message: dict) -> DomainEvent:
        """
        Deserializes the message into a DomainEvent
        :param message: SQS message
        :return: Deserialized DomainEvent
        """
        try:
            # parse SNS envelope
            sns_envelope = json.loads(message["Body"])
            # get and parse inner event
            inner_event_str = sns_envelope["Message"]
            inner_event = json.loads(inner_event_str)

            # identify event and process payload
            event_type = inner_event["event_type"]
            cls = self.router.EVENT_REGISTRY[event_type]

            # process the payload into the specific event class
            self.logger.debug(f"Event deserialized, type: {event_type}",
                              extra={"event_type": event_type, "raw_payload": inner_event})
            return cls.deserialize(inner_event)
        except Exception as e:
            self.logger.error(f"Failed to deserialize message, {message}", exc_info=e, extra={"message_raw": message})
            raise SQSDeserializationException(f"Failed to deserialize message, raw: {message}") from e

    async def _handle_event(self, event: DomainEvent, message_attributes: dict) -> None:
        """
        Handles the event by routing it to the appropriate handler
        :param event: a polled domain event
        :param message_attributes: SQS message attributes (for trace context)
        :return: None
        """
        # Extract or generate trace context
        trace_id = message_attributes.get('trace_id', {}).get('StringValue') if message_attributes else None
        if not trace_id:
            trace_id = logger.generate_trace_id()

        # Set trace context for this message processing
        logger.set_trace_context(trace_id)

        await self.router.route(event)

    async def stop_polling(self) -> None:
        """
        Stops the polling process
        :return: None
        """
        if self.run_polling:
            self.run_polling = False
            await self.sqs.close()

    async def start_polling(self):
        """
        Starts the polling process
        :return: None
        """
        if self.run_polling:
            self.logger.warning("Polling already running.")
            return
        self.logger.info(f"Polling started {self.queue_url}; interval {self.polling_time}", extra={
            "queue_url": self.queue_url, "polling_interval": self.polling_time})
        self.run_polling = True
        try:
            async with self.aws_session.client("sqs", endpoint_url=self.endpoint_url) as sqs_client:
                self.sqs = sqs_client
                while self.run_polling:
                    try:
                        response = await sqs_client.receive_message(
                            QueueUrl=self.queue_url,
                            MaxNumberOfMessages=1,
                            WaitTimeSeconds=self.polling_time,
                            MessageAttributeNames=["All"]
                        )
                        messages = response.get("Messages", [])
                        if not messages:
                            continue

                        for message in messages:
                            # Start timing for processing duration
                            start_time = time.time()

                            event = self._deserialize_event(message)
                            message_attributes = message.get("MessageAttributes", {})
                            event_age = event.get_age()

                            self.logger.info(f"Event polled, type {event.event_type}, age: {event_age}", extra={
                                "queue_url": self.queue_url,
                                "event_type": event.event_type,
                                "event_age": event_age
                            })

                            await self._handle_event(event, message_attributes)

                            await sqs_client.delete_message(
                                QueueUrl=self.queue_url,
                                ReceiptHandle=message["ReceiptHandle"]
                            )

                            # Record metrics after successful processing
                            processing_duration = time.time() - start_time

                            metrics.sqs_events_processed_total.labels(
                                event_type=event.event_type,
                                queue_name=self.consumer_name
                            ).inc()

                            metrics.sqs_event_processing_duration_seconds.labels(
                                event_type=event.event_type,
                                queue_name=self.consumer_name
                            ).observe(processing_duration)

                            metrics.sqs_event_age_seconds.labels(
                                event_type=event.event_type,
                                queue_name=self.consumer_name
                            ).observe(event_age)
                    except Exception as e:
                        self.logger.error(f"Failed to poll or process message, url {self.queue_url}", exc_info=e,
                                          extra={"queue_url": self.queue_url})
        except asyncio.CancelledError:
            self.logger.info(f"Polling task for {self.queue_url} was cancelled.", extra={"queue_url": self.queue_url})
            raise
        finally:
            try:
                await self.stop_polling()
            except Exception as e:
                self.logger.error(f"Failed to stop polling for {self.queue_url}", exc_info=e,
                                  extra={"queue_url": self.queue_url})
            self.logger.info(f"Polling stopped for {self.queue_url}", extra={"queue_url": self.queue_url})
