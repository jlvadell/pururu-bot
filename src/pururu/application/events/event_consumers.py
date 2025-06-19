import asyncio
import json
from abc import ABC, abstractmethod

import aioboto3

import pururu.config as config
from pururu.application.events.entities import PururuEvent, EventType, MemberJoinedChannelEvent, MemberLeftChannelEvent, \
    NewGameIntentEvent, EndGameIntentEvent, GameEndedEvent, GameStartedEvent, CheckExpiredPollsEvent, FinalizePollEvent
from pururu.application.services.pururu_handler import PururuHandler
from pururu.common import logger
from pururu.common.exceptions import EventDeserializationException, EventTooEarlyException


class BaseEventConsumer(ABC):
    EVENT_CLASS_MAP = {
        EventType.MEMBER_JOINED_CHANNEL.value: MemberJoinedChannelEvent,
        EventType.MEMBER_LEFT_CHANNEL.value: MemberLeftChannelEvent,
        EventType.NEW_GAME_INTENT.value: NewGameIntentEvent,
        EventType.END_GAME_INTENT.value: EndGameIntentEvent,
        EventType.GAME_ENDED.value: GameEndedEvent,
        EventType.GAME_STARTED.value: GameStartedEvent,
        EventType.CHECK_EXPIRED_POLLS.value: CheckExpiredPollsEvent,
        EventType.FINALIZE_POLL.value: FinalizePollEvent
    }

    def __init__(self, name):
        self.logger = logger.get_logger(name)
        self.aws_session = aioboto3.Session()
        self.sqs = None
        self.run_polling = False

    def _deserialize_event(self, message: dict) -> PururuEvent:
        """
        Deserializes the message into a PururuEvent
        :param message: SQS message
        :return: Deserialized PururuEvent
        """
        try:
            # parse SNS envelope
            sns_envelope = json.loads(message["Body"])
            # get and parse inner event
            inner_event_str = sns_envelope["Message"]
            inner_event = json.loads(inner_event_str)

            # identify event and process payload
            event_type = inner_event["event_type"]
            cls = self.EVENT_CLASS_MAP[event_type]

            # process the payload into the specific event class
            self.logger.debug(f"Event deserialized, type: {event_type}",
                              extra={"event_type": event_type, "raw_payload": inner_event})
            return cls.process_payload(inner_event)
        except Exception as e:
            self.logger.error(f"Failed to deserialize message, {message}", exc_info=e, extra={"message_raw": message})
            raise EventDeserializationException(f"Failed to deserialize message, raw: {message}") from e

    @abstractmethod
    def _handle_event(self, event: PururuEvent):
        pass

    async def stop_polling(self):
        if self.run_polling:
            self.run_polling = False
            await self.sqs.close()

    async def _start_generic_polling(self, queue_url: str, polling_time: int):
        """
        Starts a generic polling process for the given queue_url and polling_time
        :param queue_url: the URL of the SQS queue to poll
        :param polling_time: the time to wait between polls
        :return: None
        """
        if self.run_polling:
            self.logger.warning("Polling already running.")
            return
        self.logger.info(f"Polling started {queue_url}; interval {polling_time}",
                         extra={"queue_url": queue_url, "interval": polling_time})
        self.run_polling = True
        last_receipt_handle = None
        try:
            async with self.aws_session.client("sqs") as sqs_client:
                self.sqs = sqs_client
                while self.run_polling:
                    try:
                        response = await sqs_client.receive_message(
                            QueueUrl=queue_url,
                            MaxNumberOfMessages=1,
                            WaitTimeSeconds=polling_time,
                            MessageAttributeNames=["All"]
                        )
                        messages = response.get("Messages", [])
                        if not messages:
                            continue

                        for message in messages:
                            event = self._deserialize_event(message)
                            last_receipt_handle = message["ReceiptHandle"]
                            self.logger.info(f"Event polled, type {event.event_type}, age: {event.get_age()}", extra={
                                "queue_url": queue_url,
                                "event_type": event.event_type,
                                "event_age": event.get_age(),
                                "event_payload": event.__dict__
                            })
                            await self._handle_event(event)

                            await sqs_client.delete_message(
                                QueueUrl=queue_url,
                                ReceiptHandle=message["ReceiptHandle"]
                            )
                    except EventTooEarlyException as ex:
                        self.logger.warning("Delaying event due to being too early", extra={
                            "queue_url": queue_url,
                            "error": str(ex),
                            "visibility_timeout": config.SQS_EVENT_VISIBILITY_TIMEOUT
                        })
                        await sqs_client.change_message_visibility(
                            QueueUrl=queue_url,
                            ReceiptHandle=last_receipt_handle,
                            VisibilityTimeout=config.SQS_EVENT_VISIBILITY_TIMEOUT
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to poll or process message, url {queue_url}", exc_info=e,
                                          extra={"queue_url": queue_url})
        except asyncio.CancelledError:
            self.logger.info(f"Polling task for {queue_url} was cancelled.")
            raise
        finally:
            try:
                await self.stop_polling()
            except Exception as e:
                self.logger.error(f"Failed to stop polling for {queue_url}", exc_info=e, extra={"queue_url": queue_url})
            self.logger.info(f"Polling stopped for {queue_url}", extra={"queue_url": queue_url})


class GameEventConsumer(BaseEventConsumer):
    def __init__(self, pururu_handler: PururuHandler):
        super().__init__(__name__)
        self.queue_url = config.GAME_EVENTS_QUEUE_URL
        self.polling_time = config.EVENTS_POLLING_INTERVAL
        self.pururu_handler = pururu_handler

    async def start_polling(self):
        await super()._start_generic_polling(self.queue_url, self.polling_time)

    async def _handle_event(self, event: PururuEvent):
        self.logger.info(f"Handling game event, type: {event.event_type}", extra={"event_type": event.event_type})
        if event.event_type == EventType.MEMBER_JOINED_CHANNEL:
            self.pururu_handler.handle_member_joined_channel_event(event)
        elif event.event_type == EventType.MEMBER_LEFT_CHANNEL:
            self.pururu_handler.handle_member_left_channel_event(event)
        elif event.event_type == EventType.NEW_GAME_INTENT:
            self.pururu_handler.handle_new_game_intent_event(event)
        elif event.event_type == EventType.END_GAME_INTENT:
            self.pururu_handler.handle_end_game_intent_event(event)
        elif event.event_type == EventType.GAME_ENDED:
            self.pururu_handler.handle_game_ended_event(event)
        elif event.event_type == EventType.GAME_STARTED:
            self.pururu_handler.handle_game_started_event(event)
        else:
            self.logger.error(f"Unhandled game event of type {event.event_type}",
                              extra={"event_type": event.event_type})


class PollEventConsumer(BaseEventConsumer):
    def __init__(self, pururu_handler: PururuHandler):
        super().__init__(__name__)
        self.queue_url = config.POLL_EVENTS_QUEUE_URL
        self.polling_time = config.EVENTS_POLLING_INTERVAL
        self.pururu_handler = pururu_handler

    async def start_polling(self):
        await super()._start_generic_polling(self.queue_url, self.polling_time)

    async def _handle_event(self, event: PururuEvent):
        self.logger.info(f"Handling poll event, type: {event.event_type}", extra={"event_type": event.event_type})
        if event.event_type == EventType.CHECK_EXPIRED_POLLS:
            await self.pururu_handler.handle_check_expired_polls_event(event)
        elif event.event_type == EventType.FINALIZE_POLL:
            await self.pururu_handler.handle_finalize_poll_event(event)
        else:
            self.logger.error(f"Unhandled poll event of type {event.event_type}",
                              extra={"event_type": event.event_type})
