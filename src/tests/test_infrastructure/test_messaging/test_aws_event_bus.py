from unittest.mock import MagicMock

import pytest
from hamcrest import assert_that, equal_to

from pururu.infrastructure.adapters.aws.sns_client_adapter import SNSClientAdapter
from pururu.infrastructure.adapters.aws.sqs_client_adapter import SQSClientAdapter
from pururu.infrastructure.messaging.aws_event_bus import AWSEventBus


@pytest.fixture
def mock_sns_client():
    """Create a mock SNSClientAdapter"""
    return MagicMock(spec=SNSClientAdapter)


@pytest.fixture
def mock_sqs_adapter():
    """Create a mock SQSClientAdapter"""
    return MagicMock(spec=SQSClientAdapter)


@pytest.fixture
def event_bus(mock_sns_client, mock_sqs_adapter):
    """Create an AWSEventBus instance with mocked dependencies"""
    return AWSEventBus(mock_sns_client, mock_sqs_adapter)


@pytest.fixture
def mock_event():
    """Create a mock DomainEvent"""
    event = MagicMock()
    event.event_type = "TestEvent"
    event.priority = "Primary"
    return event


@pytest.mark.unit
def test_aws_event_bus_initialization(mock_sns_client, mock_sqs_adapter):
    """Test AWSEventBus initializes with SNS and SQS clients"""
    # Act
    event_bus = AWSEventBus(mock_sns_client, mock_sqs_adapter)

    # Assert
    assert_that(event_bus.sns_client, equal_to(mock_sns_client))
    assert_that(event_bus.sqs_adapter, equal_to(mock_sqs_adapter))


@pytest.mark.unit
def test_publish_delegates_to_sns_client(event_bus, mock_sns_client, mock_event):
    """Test publish delegates to SNS client"""
    # Act
    event_bus.publish(mock_event)

    # Assert
    mock_sns_client.publish.assert_called_once_with(mock_event)


@pytest.mark.unit
def test_subscribe_delegates_to_sqs_adapter(event_bus, mock_sqs_adapter):
    """Test subscribe delegates to SQS adapter"""
    # Arrange
    handler = MagicMock()
    event_type = "TestEvent"

    # Act
    event_bus.subscribe(event_type, handler)

    # Assert
    mock_sqs_adapter.subscribe.assert_called_once_with(event_type, handler)
