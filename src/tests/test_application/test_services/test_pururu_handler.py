from unittest.mock import patch, AsyncMock

import pytest
from freezegun import freeze_time
from hamcrest import assert_that, equal_to

from pururu.application.events.entities import (EventType, MemberJoinedChannelEvent, MemberLeftChannelEvent,
                                                NewGameIntentEvent, GameStartedEvent, EndGameIntentEvent,
                                                GameEndedEvent, CheckExpiredPollsEvent, FinalizePollEvent)
from pururu.application.services.pururu_handler import PururuHandler
from pururu.domain.entities import SessionInfo, Attendance
from pururu.common.exceptions import CannotStartNewGame, CannotEndGame, GameEndedWithoutPrecondition, \
    EventTooEarlyException
from pururu.domain.services.pururu_service import PururuService
from tests.test_application.test_events.test_entities import (member_joined_channel_event, member_left_channel_event,
                                                              new_game_intent_event, end_game_intent_event,
                                                              game_started_event, game_ended_event,
                                                              check_expired_polls_event,
                                                              finalize_poll_event)
from tests.test_domain.test_entities import session_info, attendance, poll


@patch("pururu.domain.services.event_service")
def set_up(event_service_mock) -> PururuHandler:
    pururu_handler = PururuHandler(AsyncMock(spec=PururuService), event_service_mock)
    pururu_handler.logger = AsyncMock()
    return pururu_handler


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_dc_event_player_joined():
    # Given
    pururu_handler = set_up()
    # When
    pururu_handler.handle_voice_state_update_dc_event("member1", None, "channel")
    # Then
    event = pururu_handler.event_service.publish.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.MEMBER_JOINED_CHANNEL.value))
    assert_that(event.payload["member"], equal_to("member1"))
    assert_that(event.payload["channel"], equal_to("channel"))
    pururu_handler.event_service.publish.assert_called_once()


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_dc_event_player_left_ok():
    # Given
    pururu_handler = set_up()
    # When
    pururu_handler.handle_voice_state_update_dc_event("member1", "channel", None)
    # Then
    event = pururu_handler.event_service.publish.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.MEMBER_LEFT_CHANNEL.value))
    assert_that(event.payload["member"], equal_to("member1"))
    assert_that(event.payload["channel"], equal_to("channel"))


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_dc_event_player_changed_between_channels():
    # Given
    pururu_handler = set_up()
    # When
    pururu_handler.handle_voice_state_update_dc_event("member1", "before_channel", "after_channel")
    # Then
    pururu_handler.event_service.assert_not_called()


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_dc_event_player_not_in_array():
    # Given
    pururu_handler = set_up()
    # When
    pururu_handler.handle_voice_state_update_dc_event("member15", None, "channel")
    # Then
    pururu_handler.event_service.assert_not_called()


@freeze_time("2023-08-10 10:00:00")
def test_handle_member_joined_channel_event_start_new_game_true(session_info: SessionInfo,
                                                                member_joined_channel_event: MemberJoinedChannelEvent):
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.add_player.return_value = True
    pururu_handler.domain_service.get_session_info.return_value = session_info
    # When
    pururu_handler.handle_member_joined_channel_event(member_joined_channel_event)
    pururu_handler.domain_service.should_start_new_game_session.return_value = True
    # Then
    pururu_handler.domain_service.add_player.assert_called_once_with(member_joined_channel_event.member,
                                                                     member_joined_channel_event.joined_at)
    pururu_handler.domain_service.get_session_info.assert_called_once()
    pururu_handler.event_service.publish.assert_called_once()
    event = pururu_handler.event_service.publish.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.NEW_GAME_INTENT.value))
    assert_that(event.payload["players"], equal_to(session_info.players))
    assert_that(event.payload["start_time"], equal_to("2023-08-10T10:00:00"))


def test_handle_member_joined_channel_event_start_new_game_false(session_info: SessionInfo,
                                                                 member_joined_channel_event: MemberJoinedChannelEvent):
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.add_player.return_value = False
    # When
    pururu_handler.handle_member_joined_channel_event(member_joined_channel_event)
    pururu_handler.domain_service.should_start_new_game_session.return_value = False
    # Then
    pururu_handler.domain_service.add_player.assert_called_once_with(member_joined_channel_event.member,
                                                                     member_joined_channel_event.joined_at)
    pururu_handler.event_service.assert_not_called()


@freeze_time("2023-08-10 10:00:00")
def test_handle_member_left_channel_event_end_game_true(session_info: SessionInfo,
                                                        member_left_channel_event: MemberLeftChannelEvent):
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.should_end_game_session.return_value = True
    pururu_handler.domain_service.get_session_info.return_value = session_info
    # When
    pururu_handler.handle_member_left_channel_event(member_left_channel_event)
    # Then
    pururu_handler.domain_service.remove_player.assert_called_once_with(member_left_channel_event.member,
                                                                        member_left_channel_event.left_at)
    pururu_handler.domain_service.get_session_info.assert_called_once()
    pururu_handler.event_service.publish.assert_called_once()
    event = pururu_handler.event_service.publish.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.END_GAME_INTENT.value))
    assert_that(event.payload["players"], equal_to(session_info.players))
    assert_that(event.payload["end_time"], equal_to("2023-08-10T10:00:00"))


def test_handle_member_left_channel_event_end_game_false(session_info: SessionInfo,
                                                         member_left_channel_event: MemberLeftChannelEvent):
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.should_end_game_session.return_value = False
    # When
    pururu_handler.handle_member_left_channel_event(member_left_channel_event)
    # Then
    pururu_handler.domain_service.remove_player.assert_called_once_with(member_left_channel_event.member,
                                                                        member_left_channel_event.left_at)
    pururu_handler.event_service.assert_not_called()


def test_handle_new_game_intent_event_ok(session_info: SessionInfo, new_game_intent_event: NewGameIntentEvent):
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.start_new_game.return_value = session_info
    new_game_intent_event.created_at = "2023-08-10 10:00:00"
    # When
    pururu_handler.handle_new_game_intent_event(new_game_intent_event)
    # Then
    pururu_handler.domain_service.start_new_game.assert_called_once_with(new_game_intent_event.start_time)
    pururu_handler.event_service.publish.assert_called_once()
    event = pururu_handler.event_service.publish.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.GAME_STARTED.value))
    assert_that(event.payload["game_id"], equal_to(session_info.game_id))
    assert_that(event.payload["players"], equal_to(session_info.players))


def test_handle_new_game_intent_event_cannot_start_new_game_exception(session_info: SessionInfo,
                                                                      new_game_intent_event: NewGameIntentEvent):
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.start_new_game.side_effect = CannotStartNewGame("Cannot start new game")
    new_game_intent_event.created_at = "2023-08-10 10:00:00"
    # When
    pururu_handler.handle_new_game_intent_event(new_game_intent_event)
    # Then
    pururu_handler.domain_service.start_new_game.assert_called_once_with(new_game_intent_event.start_time)
    pururu_handler.event_service.assert_not_called()


@patch("pururu.config.ATTENDANCE_CHECK_DELAY", 60)
def test_handle_new_game_intent_event_too_early_exception(new_game_intent_event: NewGameIntentEvent):
    # Given
    pururu_handler = set_up()
    # When-Then
    with pytest.raises(EventTooEarlyException):
        pururu_handler.handle_new_game_intent_event(new_game_intent_event)


def test_handle_end_game_intent_event_ok(attendance: Attendance, end_game_intent_event: EndGameIntentEvent):
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.end_game.return_value = attendance
    end_game_intent_event.created_at = "2023-08-10 10:00:00"
    # When
    pururu_handler.handle_end_game_intent_event(end_game_intent_event)
    # Then
    pururu_handler.domain_service.end_game.assert_called_once_with(end_game_intent_event.end_time)
    pururu_handler.event_service.publish.assert_called_once()
    event = pururu_handler.event_service.publish.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.GAME_ENDED.value))


def test_handle_end_game_intent_event_cannot_end_game(end_game_intent_event: EndGameIntentEvent):
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.end_game.side_effect = CannotEndGame("Cannot end game")
    end_game_intent_event.created_at = "2023-08-10 10:00:00"
    # When
    pururu_handler.handle_end_game_intent_event(end_game_intent_event)
    # Then
    pururu_handler.domain_service.end_game.assert_called_once_with(end_game_intent_event.end_time)
    pururu_handler.event_service.assert_not_called()


@patch("pururu.config.ATTENDANCE_CHECK_DELAY", 60)
def test_handle_end_game_intent_event_too_early_exception(end_game_intent_event: EndGameIntentEvent):
    # Given
    pururu_handler = set_up()
    # When-Then
    with pytest.raises(EventTooEarlyException):
        pururu_handler.handle_end_game_intent_event(end_game_intent_event)


def test_handle_end_game_intent_event_game_ended_without_precondition(end_game_intent_event: EndGameIntentEvent):
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.end_game.side_effect = GameEndedWithoutPrecondition("Game ended without precondition")
    end_game_intent_event.created_at = "2023-08-10 10:00:00"
    # When
    pururu_handler.handle_end_game_intent_event(end_game_intent_event)
    # Then
    pururu_handler.domain_service.end_game.assert_called_once_with(end_game_intent_event.end_time)
    pururu_handler.event_service.assert_not_called()


def test_handle_game_started_event_ok(game_started_event: GameStartedEvent):
    # Given
    pururu_handler = set_up()
    # When
    pururu_handler.handle_game_started_event(game_started_event)
    # Then
    pururu_handler.domain_service.assert_not_called()
    pururu_handler.event_service.assert_not_called()


def test_handle_game_ended_event_ok(game_ended_event: GameEndedEvent):
    # Given
    pururu_handler = set_up()
    # When
    pururu_handler.handle_game_ended_event(game_ended_event)
    # Then
    pururu_handler.domain_service.assert_not_called()
    pururu_handler.event_service.assert_not_called()


def test_retrieve_player_stats_ok():
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.calculate_player_stats.return_value = "stats"
    # When
    actual = pururu_handler.retrieve_player_stats("player")
    # Then
    pururu_handler.domain_service.calculate_player_stats.assert_called_once_with("player")
    pururu_handler.event_service.assert_not_called()
    assert_that(actual, equal_to("stats"))


@pytest.mark.asyncio
async def test_handle_check_expired_polls_event_ok(check_expired_polls_event: CheckExpiredPollsEvent):
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.get_expired_polls.return_value = [AsyncMock()]
    # When
    await pururu_handler.handle_check_expired_polls_event(check_expired_polls_event)
    # Then
    pururu_handler.domain_service.get_expired_polls.assert_called_once()
    pururu_handler.event_service.publish.assert_called_once()
    event = pururu_handler.event_service.publish.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.FINALIZE_POLL.value))


@pytest.mark.asyncio
async def test_handle_check_expired_polls_event_no_expired_polls(check_expired_polls_event: CheckExpiredPollsEvent):
    # Given
    pururu_handler = set_up()
    pururu_handler.domain_service.get_expired_polls.return_value = []
    # When
    await pururu_handler.handle_check_expired_polls_event(check_expired_polls_event)
    # Then
    pururu_handler.domain_service.get_expired_polls.assert_called_once()
    pururu_handler.event_service.emit_event.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.usefixtures("poll")
async def test_handle_finalize_poll_event_ok(finalize_poll_event: FinalizePollEvent):
    # Given
    pururu_handler = set_up()
    # When
    await pururu_handler.handle_finalize_poll_event(finalize_poll_event)
    # Then
    pururu_handler.domain_service.finalize_poll.assert_called_once_with(finalize_poll_event.to_poll())
    pururu_handler.event_service.assert_not_called()


def test_trigger_check_expired_polls_flow():
    # Given
    pururu_handler = set_up()
    # When
    pururu_handler.trigger_check_expired_polls_flow()
    # Then
    pururu_handler.event_service.publish.assert_called_once()
    event = pururu_handler.event_service.publish.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.CHECK_EXPIRED_POLLS.value))
