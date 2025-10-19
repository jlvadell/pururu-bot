import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hamcrest import assert_that, equal_to, instance_of

from pururu.domain.messaging.events.session_events import PlayerJoinedSessionEvent
from pururu.infrastructure.adapters.aws.sqs_client_adapter import (
    SQSClientAdapter,
    EventRouter,
    GenericSQSPoller
)
from pururu.infrastructure.exceptions import SQSDeserializationException, SQSHandlerNotFoundException


# ============================================================================
# EventRouter Tests
# ============================================================================

@pytest.fixture
def event_router():
    """Create an EventRouter instance"""
    return EventRouter()


@pytest.fixture
def mock_event():
    """Create a mock DomainEvent"""
    event = MagicMock()
    event.event_type = "TestEvent"
    return event


@pytest.mark.unit
def test_event_router_register(event_router):
    """Test EventRouter registers handlers"""
    # Arrange
    handler = MagicMock()

    # Act
    event_router.register("TestEvent", handler)

    # Assert
    assert_that(event_router._routes["TestEvent"], equal_to(handler))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_event_router_route_sync_handler(event_router, mock_event):
    """Test EventRouter routes to synchronous handler"""
    # Arrange
    handler = MagicMock(return_value="sync_result")
    event_router.register("TestEvent", handler)

    # Act
    result = await event_router.route(mock_event)

    # Assert
    handler.assert_called_once_with(mock_event)
    assert_that(result, equal_to("sync_result"))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_event_router_route_async_handler(event_router, mock_event):
    """Test EventRouter routes to asynchronous handler"""
    # Arrange
    handler = AsyncMock(return_value="async_result")
    event_router.register("TestEvent", handler)

    # Act
    result = await event_router.route(mock_event)

    # Assert
    handler.assert_awaited_once_with(mock_event)
    assert_that(result, equal_to("async_result"))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_event_router_route_raises_on_no_handler(event_router, mock_event):
    """Test EventRouter raises exception when handler not found"""
    # Arrange - no handler registered

    # Act & Assert
    with pytest.raises(SQSHandlerNotFoundException) as exc_info:
        await event_router.route(mock_event)

    assert_that("TestEvent" in str(exc_info.value), equal_to(True))


# ============================================================================
# GenericSQSPoller Tests
# ============================================================================

@pytest.fixture
def mock_router():
    """Create a mock EventRouter"""
    router = MagicMock(spec=EventRouter)
    router.EVENT_REGISTRY = {
        "PlayerJoinedSessionEvent": PlayerJoinedSessionEvent
    }
    return router


@pytest.fixture
def poller(mock_router):
    """Create a GenericSQSPoller instance"""
    return GenericSQSPoller(
        consumer_name="test_consumer",
        region="us-east-1",
        queue_url="http://localhost:4566/queue/test",
        polling_time=5,
        endpoint_url="http://localhost:4566",
        router=mock_router
    )


@pytest.mark.unit
def test_poller_deserialize_event_success(poller, mock_router):
    """Test _deserialize_event successfully deserializes SQS message"""
    # Arrange
    mock_event = MagicMock()
    PlayerJoinedSessionEvent.deserialize = MagicMock(return_value=mock_event)

    sqs_message = {
        "Body": json.dumps({
            "Message": json.dumps({
                "event_type": "PlayerJoinedSessionEvent",
                "player_id": "player123",
                "time": "2025-10-01T10:00:00"
            })
        })
    }

    # Act
    result = poller._deserialize_event(sqs_message)

    # Assert
    assert_that(result, equal_to(mock_event))
    PlayerJoinedSessionEvent.deserialize.assert_called_once()


@pytest.mark.unit
def test_poller_deserialize_event_invalid_json(poller):
    """Test _deserialize_event raises exception on invalid JSON"""
    # Arrange
    sqs_message = {"Body": "invalid json"}

    # Act & Assert
    with pytest.raises(SQSDeserializationException):
        poller._deserialize_event(sqs_message)


@pytest.mark.unit
def test_poller_deserialize_event_missing_event_type(poller):
    """Test _deserialize_event raises exception when event_type is missing"""
    # Arrange
    sqs_message = {
        "Body": json.dumps({
            "Message": json.dumps({
                "player_id": "player123"
                # missing event_type
            })
        })
    }

    # Act & Assert
    with pytest.raises(SQSDeserializationException):
        poller._deserialize_event(sqs_message)


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.infrastructure.adapters.aws.sqs_client_adapter.logger')
async def test_poller_handle_event_routes_to_router_with_trace(mock_logger_module, poller, mock_router):
    """Test _handle_event routes event through router and sets trace context"""
    # Arrange
    mock_event = MagicMock()
    mock_event.event_type = "TestEvent"
    mock_router.route = AsyncMock()
    mock_logger_module.generate_trace_id.return_value = "generated_trace_123"
    mock_logger_module.set_trace_context = MagicMock()
    message_attributes = {}

    # Act
    await poller._handle_event(mock_event, message_attributes)

    # Assert
    mock_logger_module.set_trace_context.assert_called_once()
    mock_router.route.assert_awaited_once_with(mock_event)


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.infrastructure.adapters.aws.sqs_client_adapter.logger')
async def test_poller_handle_event_extracts_trace_from_attributes(mock_logger_module, poller, mock_router):
    """Test _handle_event extracts trace_id from message attributes"""
    # Arrange
    mock_event = MagicMock()
    mock_event.event_type = "TestEvent"
    mock_router.route = AsyncMock()
    mock_logger_module.set_trace_context = MagicMock()
    
    test_trace_id = "existing_trace_456"
    message_attributes = {
        "trace_id": {
            "StringValue": test_trace_id,
            "DataType": "String"
        }
    }

    # Act
    await poller._handle_event(mock_event, message_attributes)

    # Assert
    mock_logger_module.set_trace_context.assert_called_once_with(test_trace_id)
    mock_router.route.assert_awaited_once_with(mock_event)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_poller_stop_polling_when_running(poller):
    """Test stop_polling closes SQS client when running"""
    # Arrange
    poller.run_polling = True
    poller.sqs = AsyncMock()

    # Act
    await poller.stop_polling()

    # Assert
    assert_that(poller.run_polling, equal_to(False))
    poller.sqs.close.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_poller_stop_polling_when_not_running(poller):
    """Test stop_polling does nothing when not running"""
    # Arrange
    poller.run_polling = False
    poller.sqs = AsyncMock()

    # Act
    await poller.stop_polling()

    # Assert
    poller.sqs.close.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_poller_start_polling_returns_if_already_running(poller):
    """Test start_polling returns early if already running"""
    # Arrange
    poller.run_polling = True

    # Act
    await poller.start_polling()

    # Assert - should return immediately without creating client
    assert_that(poller.run_polling, equal_to(True))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_poller_start_polling_processes_messages(poller, mock_router):
    """Test start_polling polls and processes messages"""
    # Arrange
    mock_sqs_client = AsyncMock()
    mock_event = MagicMock()
    mock_event.event_type = "PlayerJoinedSessionEvent"
    mock_event.get_age.return_value = 1.5

    # Mock receive_message to return a message once, then stop
    call_count = 0

    async def mock_receive(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "Messages": [{
                    "Body": json.dumps({
                        "Message": json.dumps({
                            "event_type": "PlayerJoinedSessionEvent",
                            "player_id": "player123"
                        })
                    }),
                    "MessageAttributes": {
                        "trace_id": {
                            "StringValue": "test_trace_123",
                            "DataType": "String"
                        }
                    },
                    "ReceiptHandle": "receipt-123"
                }]
            }
        else:
            # Stop polling after first message
            await poller.stop_polling()
            return {"Messages": []}

    mock_sqs_client.receive_message = mock_receive
    mock_sqs_client.delete_message = AsyncMock()
    mock_sqs_client.close = AsyncMock()

    poller._deserialize_event = MagicMock(return_value=mock_event)
    poller._handle_event = AsyncMock()

    # Mock the session client context manager
    with patch.object(poller.aws_session, 'client') as mock_client:
        mock_client.return_value.__aenter__.return_value = mock_sqs_client
        mock_client.return_value.__aexit__.return_value = AsyncMock()

        # Act
        await poller.start_polling()

    # Assert
    poller._deserialize_event.assert_called_once()
    # Verify _handle_event was called with event and message_attributes
    assert_that(poller._handle_event.await_count, equal_to(1))
    call_args = poller._handle_event.await_args
    assert_that(call_args[0][0], equal_to(mock_event))
    assert_that(call_args[0][1]["trace_id"]["StringValue"], equal_to("test_trace_123"))
    mock_sqs_client.delete_message.assert_awaited_once()


# ============================================================================
# SQSClientAdapter Tests
# ============================================================================

@pytest.fixture
def mock_settings():
    """Create mock settings"""
    with patch('pururu.infrastructure.adapters.aws.sqs_client_adapter.settings') as mock:
        mock.aws.sqs_queues = {
            "queue1": {
                "queue_url": "http://localhost:4566/queue/queue1",
                "endpoint_url": "http://localhost:4566"
            },
            "queue2": {
                "queue_url": "http://localhost:4566/queue/queue2",
                "endpoint_url": "http://localhost:4566",
                "polling_time": 10
            }
        }
        mock.events.aws_region = "us-east-1"
        yield mock


@pytest.fixture
def adapter(mock_settings):
    """Create an SQSClientAdapter instance"""
    return SQSClientAdapter()


@pytest.mark.unit
def test_adapter_initializes_router(adapter):
    """Test SQSClientAdapter initializes EventRouter"""
    # Assert
    assert_that(adapter.router, instance_of(EventRouter))


@pytest.mark.unit
def test_adapter_subscribe_registers_handler(adapter):
    """Test subscribe registers handler with router"""
    # Arrange
    handler = MagicMock()

    # Act
    adapter.subscribe("TestEvent", handler)

    # Assert
    assert_that(adapter.router._routes["TestEvent"], equal_to(handler))


@pytest.mark.unit
def test_adapter_registers_consumers_from_config(adapter):
    """Test _register_consumers creates pollers from queue config"""
    # Assert
    assert_that(len(adapter.queue_consumers), equal_to(2))
    assert_that(adapter.queue_consumers[0], instance_of(GenericSQSPoller))
    assert_that(adapter.queue_consumers[1], instance_of(GenericSQSPoller))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_adapter_start_polling_creates_tasks(adapter):
    """Test start_polling creates asyncio tasks for each consumer"""
    # Arrange
    for consumer in adapter.queue_consumers:
        consumer.start_polling = AsyncMock()

    # Act
    adapter.start_polling()

    # Assert
    assert_that(len(adapter.tasks), equal_to(2))
    for task in adapter.tasks:
        assert_that(task, instance_of(asyncio.Task))
        task.cancel()  # Clean up


@pytest.mark.unit
def test_adapter_stop_polling_cancels_tasks(adapter):
    """Test stop_polling cancels all running tasks"""
    # Arrange
    mock_task1 = MagicMock(spec=asyncio.Task)
    mock_task2 = MagicMock(spec=asyncio.Task)
    adapter.tasks = [mock_task1, mock_task2]

    # Act
    adapter.stop_polling()

    # Assert
    mock_task1.cancel.assert_called_once()
    mock_task2.cancel.assert_called_once()


@pytest.mark.unit
def test_adapter_stop_polling_handles_cancelled_error(adapter):
    """Test stop_polling handles CancelledError gracefully"""
    # Arrange
    mock_task = MagicMock(spec=asyncio.Task)
    mock_task.cancel.side_effect = asyncio.CancelledError()
    adapter.tasks = [mock_task]

    # Act - should not raise
    adapter.stop_polling()

    # Assert
    mock_task.cancel.assert_called_once()
