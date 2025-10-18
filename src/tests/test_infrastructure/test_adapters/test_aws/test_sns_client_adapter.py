import json
from unittest.mock import MagicMock, patch

import pytest

from pururu.domain.exceptions import EventPublishException
from pururu.infrastructure.adapters.aws.sns_client_adapter import SNSClientAdapter


@pytest.fixture
def mock_boto3():
    """Create a mock boto3"""
    with patch('pururu.infrastructure.adapters.aws.sns_client_adapter.boto3') as mock:
        yield mock


@pytest.fixture
def mock_sns_client(mock_boto3):
    """Create a mock SNS client"""
    mock_client = MagicMock(name="sns_client")
    mock_boto3.client.return_value = mock_client
    return mock_client


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    with patch('pururu.infrastructure.adapters.aws.sns_client_adapter.settings') as mock:
        mock.aws.region = "us-east-1"
        mock.aws.sns_topics.main.endpoint_url = "http://localhost:4566"
        mock.aws.sns_topics.main.topic_arn = "arn:aws:sns:us-east-1:000000000000:test-topic"
        yield mock


@pytest.fixture
def adapter(mock_boto3, mock_sns_client, mock_settings):
    """Create an SNSClientAdapter instance with mocked dependencies"""
    return SNSClientAdapter()


@pytest.fixture
def mock_event():
    """Create a mock DomainEvent"""
    event = MagicMock(name="DomainEvent")
    event.event_type = "TestEvent"
    event.priority = "Primary"
    event.serialize.return_value = {"key": "value", "data": "test"}
    event.idempotency_key.return_value = "test-idempotency-key-123"
    return event


@pytest.mark.unit
@patch('pururu.infrastructure.adapters.aws.sns_client_adapter.logger.trace_id_var')
def test_publish_success_without_trace_context(mock_trace_var, adapter, mock_sns_client, mock_event):
    """Test publish successfully sends event to SNS without trace context"""
    # Arrange
    mock_trace_var.get.return_value = None
    mock_sns_client.publish.return_value = {"MessageId": "msg-123"}
    expected_payload = json.dumps({"key": "value", "data": "test"})

    # Act
    adapter.publish(mock_event)

    # Assert
    mock_sns_client.publish.assert_called_once_with(
        TopicArn="arn:aws:sns:us-east-1:000000000000:test-topic",
        Message=expected_payload,
        MessageAttributes={
            "queue_priority": {
                "DataType": "String",
                "StringValue": "Primary"
            }
        },
        MessageGroupId="TestEvent",
        MessageDeduplicationId="test-idempotency-key-123"
    )


@pytest.mark.unit
@patch('pururu.infrastructure.adapters.aws.sns_client_adapter.logger.trace_id_var')
def test_publish_success_with_trace_context(mock_trace_var, adapter, mock_sns_client, mock_event):
    """Test publish successfully sends event to SNS with trace context propagated"""
    # Arrange
    test_trace_id = "abc123def456"
    mock_trace_var.get.return_value = test_trace_id
    mock_sns_client.publish.return_value = {"MessageId": "msg-123"}
    expected_payload = json.dumps({"key": "value", "data": "test"})

    # Act
    adapter.publish(mock_event)

    # Assert
    mock_sns_client.publish.assert_called_once_with(
        TopicArn="arn:aws:sns:us-east-1:000000000000:test-topic",
        Message=expected_payload,
        MessageAttributes={
            "queue_priority": {
                "DataType": "String",
                "StringValue": "Primary"
            },
            "trace_id": {
                "DataType": "String",
                "StringValue": test_trace_id
            }
        },
        MessageGroupId="TestEvent",
        MessageDeduplicationId="test-idempotency-key-123"
    )


@pytest.mark.unit
def test_publish_raises_on_sns_error(adapter, mock_sns_client, mock_event):
    """Test publish raises EventPublishException when SNS publish fails"""
    # Arrange
    mock_sns_client.publish.side_effect = Exception("SNS API Error")

    # Act & Assert
    with pytest.raises(EventPublishException):
        adapter.publish(mock_event)
