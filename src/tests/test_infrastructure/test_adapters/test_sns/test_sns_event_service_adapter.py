import json
from unittest.mock import Mock, patch

import pytest

from pururu.common.exceptions import SNSPublishException
from pururu.infrastructure.adapters.sns.sns_event_service_adapter import SNSEventServiceAdapter


@patch('pururu.infrastructure.adapters.sns.sns_event_service_adapter.boto3')
@patch('pururu.common.utils.get_logger')
@patch('pururu.config.SNS_TOPIC_ARN', 'arn:test:id:topic')
def set_up(boto3_mock, logger_mock) -> SNSEventServiceAdapter:
    sns_mock = Mock()
    boto3_mock.client.return_value = sns_mock
    adapter = SNSEventServiceAdapter()
    return adapter


def test_publish_should_call_sns_publish():
    # Given
    adapter = set_up()
    event = Mock()
    event.payload = {"a": 1, "b": 2}
    event.event_type = "test_event"
    event.get_idempotency_key.return_value = "test_idempotency_key"
    # When
    adapter.publish(event)
    # Then
    adapter.sns.publish.assert_called_once_with(
        TopicArn='arn:test:id:topic',
        Message=json.dumps(event.payload),
        MessageAttributes={
            "event_type": {
                "DataType": "String",
                "StringValue": event.event_type
            }
        },
        MessageGroupId=event.event_type,
        MessageDeduplicationId=event.get_idempotency_key()
    )


def test_publish_should_throw_exception_on_error():
    # Given
    adapter = set_up()
    event = Mock()
    event.payload = {"a": 1, "b": 2}
    event.event_type = "test_event"
    event.get_idempotency_key.return_value = "test_idempotency_key"
    adapter.sns.publish.side_effect = Exception("Test exception")
    # When
    with pytest.raises(SNSPublishException):
        adapter.publish(event)
    # Then
    adapter.sns.publish.assert_called_once_with(
        TopicArn='arn:test:id:topic',
        Message=json.dumps(event.payload),
        MessageAttributes={
            "event_type": {
                "DataType": "String",
                "StringValue": event.event_type
            }
        },
        MessageGroupId=event.event_type,
        MessageDeduplicationId=event.get_idempotency_key()
    )
