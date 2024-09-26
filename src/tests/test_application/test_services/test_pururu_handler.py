from datetime import datetime
from unittest.mock import patch

from freezegun import freeze_time
from hamcrest import assert_that, equal_to

from pururu.application.events.entities import EventType, MemberJoinedChannelEvent, MemberLeftChannelEvent, \
    NewGameIntentEvent, GameStartedEvent, EndGameIntentEvent, GameEndedEvent
from pururu.application.services.pururu_handler import PururuHandler
from pururu.domain.entities import SessionInfo, Attendance
from pururu.domain.exceptions import CannotStartNewGame, CannotEndGame, GameEndedWithoutPrecondition
from tests.test_application.test_events.test_entities import member_joined_channel_event, member_left_channel_event, \
    new_game_intent_event, end_game_intent_event, game_started_event, game_ended_event
from tests.test_domain.test_entities import session_info, attendance


@patch("pururu.domain.services.pururu_service.PururuService")
@patch("pururu.application.events.event_system.EventSystem")
def set_up(event_system_mock, pururu_service_mock) -> PururuHandler:
    return PururuHandler(pururu_service_mock, event_system_mock)


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_dc_event_player_joined():
    # Given
    handler = set_up()
    # When
    handler.handle_voice_state_update_dc_event("member1", None, "channel")
    # Then
    event = handler.event_system.emit_event.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.MEMBER_JOINED_CHANNEL))
    assert_that(type(event), equal_to(MemberJoinedChannelEvent))
    assert_that(event.member, equal_to("member1"))
    assert_that(event.channel, equal_to("channel"))
    handler.event_system.emit_event.assert_called_once()
    handler.event_system.emit_event_with_delay.assert_not_called()


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_dc_event_player_left_ok():
    # Given
    handler = set_up()
    # When
    handler.handle_voice_state_update_dc_event("member1", "channel", None)
    # Then
    event = handler.event_system.emit_event.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.MEMBER_LEFT_CHANNEL))
    assert_that(type(event), equal_to(MemberLeftChannelEvent))
    assert_that(event.member, equal_to("member1"))
    assert_that(event.channel, equal_to("channel"))


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_dc_event_player_changed_between_channels():
    # Given
    handler = set_up()
    # When
    handler.handle_voice_state_update_dc_event("member1", "before_channel", "after_channel")
    # Then
    handler.event_system.assert_not_called()


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_dc_event_player_not_in_array():
    # Given
    handler = set_up()
    # When
    handler.handle_voice_state_update_dc_event("member15", None, "channel")
    # Then
    handler.event_system.assert_not_called()


@patch("pururu.config.ATTENDANCE_CHECK_DELAY", 100)
@freeze_time("2023-08-10 10:00:00")
def test_handle_member_joined_channel_event_start_new_game_true(session_info: SessionInfo,
                                                                member_joined_channel_event: MemberJoinedChannelEvent):
    # Given
    handler = set_up()
    handler.domain_service.add_player.return_value = True
    handler.domain_service.get_session_info.return_value = session_info
    # When
    handler.handle_member_joined_channel_event(member_joined_channel_event)
    # Then
    handler.domain_service.add_player.assert_called_once_with(member_joined_channel_event.member,
                                                              member_joined_channel_event.joined_at)
    handler.domain_service.get_session_info.assert_called_once()
    handler.event_system.emit_event_with_delay.assert_called_once()
    event, time = handler.event_system.emit_event_with_delay.call_args[0]
    assert_that(event.event_type, equal_to(EventType.NEW_GAME_INTENT))
    assert_that(event.players, equal_to(session_info.players))
    assert_that(event.start_time, equal_to(datetime(2023, 8, 10, 10)))
    assert_that(time, equal_to(100))


def test_handle_member_joined_channel_event_start_new_game_false(session_info: SessionInfo,
                                                                 member_joined_channel_event: MemberJoinedChannelEvent):
    # Given
    handler = set_up()
    handler.domain_service.add_player.return_value = False
    # When
    handler.handle_member_joined_channel_event(member_joined_channel_event)
    # Then
    handler.domain_service.add_player.assert_called_once_with(member_joined_channel_event.member,
                                                              member_joined_channel_event.joined_at)
    handler.event_system.assert_not_called()


@patch("pururu.config.ATTENDANCE_CHECK_DELAY", 100)
@freeze_time("2023-08-10 10:00:00")
def test_handle_member_left_channel_event_end_game_true(session_info: SessionInfo,
                                                        member_left_channel_event: MemberLeftChannelEvent):
    # Given
    handler = set_up()
    handler.domain_service.remove_player.return_value = True
    handler.domain_service.get_session_info.return_value = session_info
    # When
    handler.handle_member_left_channel_event(member_left_channel_event)
    # Then
    handler.domain_service.remove_player.assert_called_once_with(member_left_channel_event.member,
                                                                 member_left_channel_event.left_at)
    handler.domain_service.get_session_info.assert_called_once()
    handler.event_system.emit_event_with_delay.assert_called_once()
    event, time = handler.event_system.emit_event_with_delay.call_args[0]
    assert_that(event.event_type, equal_to(EventType.END_GAME_INTENT))
    assert_that(event.players, equal_to(session_info.players))
    assert_that(event.end_time, equal_to(datetime(2023, 8, 10, 10)))
    assert_that(time, equal_to(100))


def test_handle_member_left_channel_event_end_game_false(session_info: SessionInfo,
                                                         member_left_channel_event: MemberLeftChannelEvent):
    # Given
    handler = set_up()
    handler.domain_service.add_player.return_value = False
    # When
    handler.handle_member_left_channel_event(member_left_channel_event)
    # Then
    handler.domain_service.remove_player.assert_called_once_with(member_left_channel_event.member,
                                                                 member_left_channel_event.left_at)
    handler.event_system.assert_not_called()


def test_handle_new_game_intent_event_ok(session_info: SessionInfo, new_game_intent_event: NewGameIntentEvent):
    # Given
    handler = set_up()
    handler.domain_service.start_new_game.return_value = session_info
    # When
    handler.handle_new_game_intent_event(new_game_intent_event)
    # Then
    handler.domain_service.start_new_game.assert_called_once_with(new_game_intent_event.start_time)
    handler.event_system.emit_event.assert_called_once()
    event = handler.event_system.emit_event.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.GAME_STARTED))
    assert_that(type(event), equal_to(GameStartedEvent))
    assert_that(event.game_id, equal_to(session_info.game_id))
    assert_that(event.players, equal_to(session_info.players))


def test_handle_new_game_intent_event_cannot_start_new_game(session_info: SessionInfo,
                                                            new_game_intent_event: NewGameIntentEvent):
    # Given
    handler = set_up()
    handler.domain_service.start_new_game.side_effect = CannotStartNewGame("Cannot start new game")
    # When
    handler.handle_new_game_intent_event(new_game_intent_event)
    # Then
    handler.domain_service.start_new_game.assert_called_once_with(new_game_intent_event.start_time)
    handler.event_system.assert_not_called()


def test_handle_end_game_intent_event_ok(attendance: Attendance, end_game_intent_event: EndGameIntentEvent):
    # Given
    handler = set_up()
    handler.domain_service.end_game.return_value = attendance
    # When
    handler.handle_end_game_intent_event(end_game_intent_event)
    # Then
    handler.domain_service.end_game.assert_called_once_with(end_game_intent_event.end_time)
    handler.event_system.emit_event.assert_called_once()
    event = handler.event_system.emit_event.call_args[0][0]
    assert_that(event.event_type, equal_to(EventType.GAME_ENDED))
    assert_that(type(event), equal_to(GameEndedEvent))


def test_handle_end_game_intent_event_cannot_end_game(end_game_intent_event: EndGameIntentEvent):
    # Given
    handler = set_up()
    handler.domain_service.end_game.side_effect = CannotEndGame("Cannot end game")
    # When
    handler.handle_end_game_intent_event(end_game_intent_event)
    # Then
    handler.domain_service.end_game.assert_called_once_with(end_game_intent_event.end_time)
    handler.event_system.assert_not_called()


def test_handle_end_game_intent_event_game_ended_without_precondition(end_game_intent_event: EndGameIntentEvent):
    # Given
    handler = set_up()
    handler.domain_service.end_game.side_effect = GameEndedWithoutPrecondition("Game ended without precondition")
    # When
    handler.handle_end_game_intent_event(end_game_intent_event)
    # Then
    handler.domain_service.end_game.assert_called_once_with(end_game_intent_event.end_time)
    handler.event_system.assert_not_called()


def test_handle_game_started_event_ok(game_started_event: GameStartedEvent):
    # Given
    handler = set_up()
    # When
    handler.handle_game_started_event(game_started_event)
    # Then
    handler.domain_service.assert_not_called()
    handler.event_system.assert_not_called()


def test_handle_game_ended_event_ok(game_ended_event: GameEndedEvent):
    # Given
    handler = set_up()
    # When
    handler.handle_game_ended_event(game_ended_event)
    # Then
    handler.domain_service.assert_not_called()
    handler.event_system.assert_not_called()


def test_retrieve_player_stats_ok():
    # Given
    handler = set_up()
    handler.domain_service.calculate_player_stats.return_value = "stats"
    # When
    actual = handler.retrieve_player_stats("player")
    # Then
    handler.domain_service.calculate_player_stats.assert_called_once_with("player")
    handler.event_system.assert_not_called()
    assert_that(actual, equal_to("stats"))
