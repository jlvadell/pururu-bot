import datetime
import json

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from hamcrest import assert_that, instance_of

from pururu.application.events.event_consumers import GameEventConsumer, PollEventConsumer, BaseEventConsumer
from pururu.application.services.pururu_handler import PururuHandler
from pururu.application.events.entities import EventType, MemberJoinedChannelEvent, MemberLeftChannelEvent, \
    NewGameIntentEvent, EndGameIntentEvent, GameEndedEvent, GameStartedEvent, CheckExpiredPollsEvent, FinalizePollEvent, \
    PururuEvent
from common.exceptions import EventDeserializationException


def set_up_game_consumer():
    mock_pururu_handler = MagicMock(spec=PururuHandler)
    consumer = GameEventConsumer(mock_pururu_handler)
    return consumer


def set_up_poll_consumer():
    mock_pururu_handler = MagicMock(spec=PururuHandler)
    consumer = PollEventConsumer(mock_pururu_handler)
    return consumer


# ---------------------------
# GAME EVENT CONSUMER
# ---------------------------

@pytest.mark.asyncio
async def test_game_event_consumer_handle_member_joined_channel_event():
    # Given
    consumer = set_up_game_consumer()
    event = MagicMock(spec=PururuEvent)
    event.event_type = EventType.MEMBER_JOINED_CHANNEL
    # When
    await consumer._handle_event(event)
    # Then
    consumer.pururu_handler.handle_member_joined_channel_event.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_game_event_consumer_handle_member_left_channel_event():
    # Given
    consumer = set_up_game_consumer()
    event = MagicMock(spec=PururuEvent)
    event.event_type = EventType.MEMBER_LEFT_CHANNEL
    # When
    await consumer._handle_event(event)
    # Then
    consumer.pururu_handler.handle_member_left_channel_event.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_game_event_consumer_handle_new_game_intent_event():
    # Given
    consumer = set_up_game_consumer()
    event = MagicMock(spec=PururuEvent)
    event.event_type = EventType.NEW_GAME_INTENT
    # When
    await consumer._handle_event(event)
    # Then
    consumer.pururu_handler.handle_new_game_intent_event.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_game_event_consumer_handle_end_game_intent_event():
    # Given
    consumer = set_up_game_consumer()
    event = MagicMock(spec=PururuEvent)
    event.event_type = EventType.END_GAME_INTENT
    # When
    await consumer._handle_event(event)
    # Then
    consumer.pururu_handler.handle_end_game_intent_event.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_game_event_consumer_handle_game_ended_event():
    # Given
    consumer = set_up_game_consumer()
    event = MagicMock(spec=PururuEvent)
    event.event_type = EventType.GAME_ENDED
    # When
    await consumer._handle_event(event)
    # Then
    consumer.pururu_handler.handle_game_ended_event.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_game_event_consumer_handle_game_started_event():
    # Given
    consumer = set_up_game_consumer()
    event = MagicMock(spec=PururuEvent)
    event.event_type = EventType.GAME_STARTED
    # When
    await consumer._handle_event(event)
    # Then
    consumer.pururu_handler.handle_game_started_event.assert_called_once_with(event)


# ---------------------------
# POLL EVENT CONSUMER
# ---------------------------

@pytest.mark.asyncio
async def test_poll_event_consumer_handle_check_expired_polls_event():
    # Given
    consumer = set_up_poll_consumer()
    event = MagicMock(spec=PururuEvent)
    event.event_type = EventType.CHECK_EXPIRED_POLLS
    # When
    await consumer._handle_event(event)
    # Then
    consumer.pururu_handler.handle_check_expired_polls_event.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_poll_event_consumer_handle_finalize_poll_event():
    # Given
    consumer = set_up_poll_consumer()
    event = MagicMock(spec=PururuEvent)
    event.event_type = EventType.FINALIZE_POLL
    # When
    await consumer._handle_event(event)
    # Then
    consumer.pururu_handler.handle_finalize_poll_event.assert_called_once_with(event)


# ---------------------------
# COMMON TESTS
# ---------------------------

@pytest.mark.asyncio
async def test_base_event_consumer_deserialize_event():
    # Given
    consumer = set_up_game_consumer()
    message = {
        "Body": json.dumps({"payload": {
            "member": "test",
            "channel": "test",
            "joined_at": "2023-03-03T12:00:00",
            "created_at": "2023-03-03T12:00:00"
        }}),
        "MessageAttributes": {"event_type": {"StringValue": EventType.MEMBER_JOINED_CHANNEL}}
    }
    # When
    event = consumer._deserialize_event(message)
    # Then
    assert_that(event, instance_of(MemberJoinedChannelEvent))


@pytest.mark.asyncio
async def test_base_event_consumer_deserialize_event_exception():
    consumer = GameEventConsumer(MagicMock(spec=PururuHandler))
    message = {
        "Body": "invalid json",
        "MessageAttributes": {"event_type": {"StringValue": EventType.MEMBER_JOINED_CHANNEL}}
    }

    with pytest.raises(EventDeserializationException):
        consumer._deserialize_event(message)


@patch('pururu.config.GAME_EVENTS_QUEUE_URL', "test_queue_url")
@patch('src.pururu.application.events.event_consumers.boto3.client')
@patch('src.pururu.application.events.event_consumers.utils')
@pytest.mark.asyncio
async def test_start_generic_polling(mock_utils, mock_boto3_client):
    # Given
    mock_sqs = mock_boto3_client.return_value
    mock_logger = MagicMock()
    mock_utils.get_logger.return_value = mock_logger

    # Set up the consumer
    consumer = set_up_game_consumer()
    consumer._deserialize_event = MagicMock(
        return_value=MemberJoinedChannelEvent(
            member="test",
            channel="test",
            joined_at=datetime.datetime(2023, 3, 3, 12, 0, 0)
        )
    )
    consumer._handle_event = AsyncMock()

    # Inject dummy receipt handle
    dummy_receipt_handle = "test_receipt_handle"

    def fake_receive_message(**kwargs):
        consumer.stop_polling()  # stop after first poll
        return {
            "Messages": [{
                "Body": json.dumps({
                    "payload": {
                        "member": "test",
                        "channel": "test",
                        "joined_at": "2023-03-03T12:00:00",
                        "created_at": "2023-03-03T12:00:00"
                    }
                }),
                "MessageAttributes": {
                    "event_type": {"StringValue": EventType.MEMBER_JOINED_CHANNEL}
                },
                "ReceiptHandle": dummy_receipt_handle
            }]
        }

    mock_sqs.receive_message.side_effect = fake_receive_message

    # Dummy delete
    mock_sqs.delete_message = MagicMock()

    # When
    await consumer.start_polling()

    # Then
    consumer._deserialize_event.assert_called_once()
    consumer._handle_event.assert_awaited_once()
    mock_sqs.delete_message.assert_called_once_with(
        QueueUrl="test_queue_url",  # Replace with your config if needed
        ReceiptHandle=dummy_receipt_handle
    )
