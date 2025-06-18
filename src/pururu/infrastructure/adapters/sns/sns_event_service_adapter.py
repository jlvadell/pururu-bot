import json

import boto3

import pururu.config as config
from pururu.common import utils
from pururu.common.exceptions import SNSPublishException
from pururu.domain.entities import BotEvent
from pururu.domain.services.event_service import EventService


class SNSEventServiceAdapter(EventService):
    def __init__(self):
        self.logger = utils.get_logger(__name__)
        self.sns = boto3.client("sns")
        self.topic_arn = config.SNS_TOPIC_ARN

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
            self.logger.debug(f"Event published to SNS: {event.event_type}, response: {response}")
        except Exception as e:
            self.logger.error(f"Failed to publish event: {event.event_type}, error: {e}")
            raise SNSPublishException(f"Error Publishing BotEvent: {event}") from e