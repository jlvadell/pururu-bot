import json

import boto3

from pururu.common import logger
from pururu.common.exceptions import SNSPublishException
from pururu.config import settings
from pururu.domain.entities import BotEvent
from pururu.domain.services.event_service import EventService


class SNSEventServiceAdapter(EventService):
    def __init__(self):
        self.logger = logger.get_logger(__name__)
        self.sns = boto3.client("sns", region_name=settings.events.aws_region, endpoint_url=settings.events.aws_sns_endpoint_url)
        self.topic_arn = settings.events.sns_topic_arn

    def publish(self, event: BotEvent) -> None:
        """
        Publishes a message to an SNS Topic.
        :param event: bot event
        :return: None
        """
        try:
            payload = json.dumps(event.payload)
            response = self.sns.publish(
                TopicArn=self.topic_arn,
                Message=payload,
                MessageAttributes={
                    "event_type": {
                        "DataType": "String",
                        "StringValue": event.event_type
                    }
                },
                MessageGroupId=event.event_type,
                MessageDeduplicationId=event.get_idempotency_key()
            )
            self.logger.debug(f"Event of type {event.event_type} successfully published to SNS", extra={
                "event_type": event.event_type,
                "message_id": response.get("MessageId"),
                "idempotency_key": event.get_idempotency_key()
            })
        except Exception as e:
            self.logger.error(f"SNS failed to publish event of type {event.event_type}", exc_info=True, extra={
                "event_type": event.event_type,
                "payload": event.payload,
                "idempotency_key": event.get_idempotency_key()
            })
            raise SNSPublishException(f"Error Publishing BotEvent: {event}") from e
