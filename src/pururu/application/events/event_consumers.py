from abc import ABC, abstractmethod
from datetime import datetime

import boto3
import json

import pururu.config as config
from pururu.common.exceptions import EventDeserializationException
from pururu.application.services.pururu_handler import PururuHandler
from pururu.common import utils
from pururu.application.events.entities import PururuEvent, EventType, MemberJoinedChannelEvent, MemberLeftChannelEvent, \
    NewGameIntentEvent, EndGameIntentEvent, GameEndedEvent, GameStartedEvent, CheckExpiredPollsEvent, FinalizePollEvent

class BaseEventConsumer(ABC):
    EVENT_CLASS_MAP = {
        EventType.MEMBER_JOINED_CHANNEL: MemberJoinedChannelEvent,
        EventType.MEMBER_LEFT_CHANNEL: MemberLeftChannelEvent,
        EventType.NEW_GAME_INTENT: NewGameIntentEvent,
        EventType.END_GAME_INTENT: EndGameIntentEvent,
        EventType.GAME_ENDED: GameEndedEvent,
        EventType.GAME_STARTED: GameStartedEvent,
        EventType.CHECK_EXPIRED_POLLS: CheckExpiredPollsEvent,
        EventType.FINALIZE_POLL: FinalizePollEvent
    }

    def __init__(self, name):
        self.logger = utils.get_logger(name)
        self.sqs = boto3.client("sqs")
        self.run_polling = False

    def _deserialize_event(self, message: dict) -> PururuEvent:
        """
        Deserializes the message into a PururuEvent
        :param message: SQS message
        :return: Deserialized PururuEvent
        """
        try:
            body = json.loads(message["Body"])
            event_type = message["MessageAttributes"]["event_type"]["StringValue"]
            cls = self.EVENT_CLASS_MAP[event_type]
            return cls.process_payload(body.get("payload", {}))
        except Exception as e:
            raise EventDeserializationException(f"Failed to deserialize message, raw: {message}") from e

    @abstractmethod
    def _handle_event(self, event: PururuEvent):
        pass

    def stop_polling(self):
        self.run_polling = False
        self.logger.info("Polling stopped")

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
        self.logger.info("polling started")
        self.run_polling = True
        while self.run_polling:
            try:
                response = self.sqs.receive_message(
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
                    event_age = datetime.now() - utils.parse_time(event.created_at)
                    self.logger.debug(
                        f"Event Polled, Event type {event.event_type}, Event age: {event_age.total_seconds()}s")
                    await self._handle_event(event)

                    self.sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message["ReceiptHandle"]
                    )
            except Exception as e:
                self.logger.error(f"Failed to poll or process message: {e}")


class GameEventConsumer(BaseEventConsumer):
    def __init__(self, pururu_handler: PururuHandler):
        super().__init__(__name__)
        self.queue_url = config.GAME_EVENTS_QUEUE_URL
        self.polling_time = config.EVENTS_POLLING_INTERVAL
        self.pururu_handler = pururu_handler

    async def start_polling(self):
        await super()._start_generic_polling(self.queue_url, self.polling_time)

    async def _handle_event(self, event: PururuEvent):
        self.logger.info(f"Handling event: {event.event_type}")
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
            self.logger.warning(f"Unhandled game event type: {event.event_type}")


class PollEventConsumer(BaseEventConsumer):
    def __init__(self, pururu_handler: PururuHandler):
        super().__init__(__name__)
        self.queue_url = config.POLL_EVENTS_QUEUE_URL
        self.polling_time = config.EVENTS_POLLING_INTERVAL
        self.pururu_handler = pururu_handler

    async def start_polling(self):
        await super()._start_generic_polling(self.queue_url, self.polling_time)

    async def _handle_event(self, event: PururuEvent):
        self.logger.info(f"Handling event: {event.event_type}")
        if event.event_type == EventType.CHECK_EXPIRED_POLLS:
            await self.pururu_handler.handle_check_expired_polls_event(event)
        elif event.event_type == EventType.FINALIZE_POLL:
            await self.pururu_handler.handle_finalize_poll_event(event)
        else:
            self.logger.warning(f"Unhandled poll event type: {event.event_type}")
