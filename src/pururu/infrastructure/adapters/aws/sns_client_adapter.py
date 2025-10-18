import json

import boto3

from pururu.common import logger
from pururu.config import settings
from pururu.domain.exceptions import EventPublishException
from pururu.domain.messaging.events.base_events import DomainEvent


class SNSClientAdapter:
    def __init__(self):
        self.logger = logger.get_logger(__name__)
        self.sns = boto3.client("sns", region_name=settings.aws.region,
                                endpoint_url=settings.aws.sns_topics.main.endpoint_url)
        self.topic_arn = settings.aws.sns_topics.main.topic_arn

    def publish(self, event: DomainEvent) -> None:
        """
        Publishes a message to an SNS Topic.
        :param event: bot event
        :return: None
        """
        try:
            payload = json.dumps(event.serialize())
            
            # Get current trace_id from context to propagate through SNS/SQS
            trace_id = logger.trace_id_var.get()
            
            message_attributes = {
                "queue_priority": {
                    "DataType": "String",
                    "StringValue": event.priority
                }
            }
            
            # Include trace_id for distributed tracing if available
            if trace_id:
                message_attributes["trace_id"] = {
                    "DataType": "String",
                    "StringValue": trace_id
                }
            
            response = self.sns.publish(
                TopicArn=self.topic_arn,
                Message=payload,
                MessageAttributes=message_attributes,
                MessageGroupId=event.event_type,
                MessageDeduplicationId=event.idempotency_key()
            )
            self.logger.debug(
                f"Event of type {event.event_type} successfully published to SNS, priority {event.priority}", extra={
                    "event_type": event.event_type,
                    "aws_message_id": response.get("MessageId"),
                    "idempotency_key": event.idempotency_key()
                })
        except Exception as e:
            self.logger.error(f"SNS failed to publish event of type {event.event_type} with priority {event.priority}",
                              exc_info=True, extra={
                    "event_type": event.event_type,
                    "idempotency_key": event.idempotency_key()
                })
            raise EventPublishException(
                f"Error publishing event {event.event_type} with priority {event.priority}") from e
