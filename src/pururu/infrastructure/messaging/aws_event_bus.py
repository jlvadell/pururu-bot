from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.base_events import DomainEvent
from pururu.infrastructure.adapters.aws.sns_client_adapter import SNSClientAdapter
from pururu.infrastructure.adapters.aws.sqs_client_adapter import SQSClientAdapter


class AWSEventBus(EventBus):
    def __init__(self, sns_client: SNSClientAdapter, sqs_adapter: SQSClientAdapter):
        self.sns_client = sns_client
        self.sqs_adapter = sqs_adapter

    def publish(self, event: DomainEvent) -> None:
        """
        Publishes a message to an SNS Topic.
        :param event: bot event
        :return: None
        """
        self.sns_client.publish(event)

    def subscribe(self, event_type: str, handler) -> None:
        """
        Subscribes a handler to an event type.
        :param event_type: the type of event to subscribe to
        :param handler: callable that takes a DomainEvent as parameter
        :return: None
        """
        self.sqs_adapter.subscribe(event_type, handler)
