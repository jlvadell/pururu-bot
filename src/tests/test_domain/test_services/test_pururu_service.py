from unittest.mock import patch

import pytest
from freezegun import freeze_time
from hamcrest import assert_that, equal_to, has_key, is_not

from pururu.application.events.entities import MemberJoinedChannelEvent, MemberLeftChannelEvent, NewGameIntentEvent, \
    EndGameIntentEvent, GameStartedEvent, GameEndedEvent
from pururu.application.events.event_system import EventType
from pururu.domain.entities import BotEvent, Attendance
from pururu.domain.services.pururu_service import PururuService
from tests.test_domain.test_entities import attendance


@patch('pururu.application.events.event_system.EventSystem')
@patch('pururu.domain.services.database_service.DatabaseInterface')
def set_up(db_mock, event_mock) -> PururuService:
    return PururuService(db_mock, event_mock)


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_player_joined_ok():
    service = set_up()
    service.handle_voice_state_update("member1", None, "channel")
    event_type, event = service.event_system.emit_event.call_args[0]
    assert_that(event_type, equal_to(EventType.MEMBER_JOINED_CHANNEL))
    assert_that(type(event), equal_to(MemberJoinedChannelEvent))
    assert_that(event.member, equal_to("member1"))
    assert_that(event.channel, equal_to("channel"))
    service.event_system.emit_event.assert_called_once()
    service.event_system.emit_event_with_delay.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_player_left_ok():
    service = set_up()
    service.handle_voice_state_update("member1", "channel", None)
    event_type, event = service.event_system.emit_event.call_args[0]
    assert_that(event_type, equal_to(EventType.MEMBER_LEFT_CHANNEL))
    assert_that(type(event), equal_to(MemberLeftChannelEvent))
    assert_that(event.member, equal_to("member1"))
    assert_that(event.channel, equal_to("channel"))
    service.event_system.emit_event.assert_called_once()
    service.event_system.emit_event_with_delay.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_player_changed_channels():
    service = set_up()
    service.handle_voice_state_update("member1", "before_channel", "after_channel")
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()

@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_player_changed_channels_same_name():
    service = set_up()
    service.handle_voice_state_update("member1", "channel", "channel")
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.PLAYERS", ["member1", "member2", "member3"])
def test_handle_voice_state_update_player_not_in_array():
    service = set_up()
    service.handle_voice_state_update("member15", None, "channel")
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()


def test_register_bot_event():
    service = set_up()
    event = BotEvent(
        event_type="event_type",
        date="2023-08-10",
        description="Bot event description"
    )
    service.register_bot_event(event)
    service.event_system.assert_not_called()
    service.database_service.insert_bot_event.assert_called_once_with(event)


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10 10:00:00")
def test_register_new_player_ok(utils_mock):
    service = set_up()
    service.register_new_player("member1")
    assert_that(service.players, equal_to(["member1"]))
    assert_that(service.current_game['players'], has_key("member1"))
    assert_that(service.current_game['players']["member1"], equal_to("2023-08-10 10:00:00"))
    assert_that(service.current_game['players_out'], has_key("member1"))
    assert_that(service.current_game['players_out']["member1"], equal_to(None))
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()

@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10 10:30:00")
def test_register_new_player_player_rejoined(utils_mock):
    service = set_up()
    service.players = ["member2"]
    service.current_game['players'] = {"member1": "2023-08-10 10:00:00", "member2": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member1": "2023-08-10 10:25:00", "member2": None}
    service.register_new_player("member1")
    assert_that(service.players, equal_to(["member2", "member1"]))
    assert_that(service.current_game['players'], has_key("member1"))
    assert_that(service.current_game['players']["member1"], equal_to("2023-08-10 10:00:00"))
    assert_that(service.current_game['players_out'], has_key("member1"))
    assert_that(service.current_game['players_out']["member1"], equal_to(None))
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
def test_register_new_player_already_in():
    service = set_up()
    service.players = ["member2"]
    service.current_game['players'] = {"member2": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member2": None}
    service.register_new_player("member2")
    assert_that(service.players, equal_to(["member2"]))
    assert_that(service.current_game['players'], has_key("member2"))
    assert_that(service.current_game['players']["member2"], equal_to("2023-08-10 10:00:00"))
    assert_that(service.current_game['players_out'], has_key("member2"))
    assert_that(service.current_game['players_out']["member2"], equal_to(None))
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
@patch("pururu.config.ATTENDANCE_CHECK_DELAY", 1000)
def test_register_new_player_emit_intent():
    service = set_up()
    service.players = ["member1", "member2"]
    service.register_new_player("member3")
    event_type, event, delay = service.event_system.emit_event_with_delay.call_args[0]
    assert_that(event_type, equal_to(EventType.NEW_GAME_INTENT))
    assert_that(type(event), equal_to(NewGameIntentEvent))
    assert_that(event.players, equal_to(["member1", "member2", "member3"]))
    assert_that(delay, equal_to(1000))
    service.event_system.emit_event_with_delay.assert_called_once()
    service.event_system.emit_event.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 1)
def test_remove_player_ok():
    service = set_up()
    service.players = ["member1", "member2"]
    service.current_game["game_id"] = 1
    service.current_game['players'] = {"member1": "2023-08-10 10:00:00", "member2": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member1": None, "member2": None}
    service.remove_player("member1")
    assert_that(service.players, equal_to(["member2"]))
    assert_that(service.current_game['players'], has_key("member1"))
    assert_that(service.current_game['players']["member1"], equal_to("2023-08-10 10:00:00"))
    assert_that(service.current_game['players'], has_key("member2"))
    assert_that(service.current_game['players']["member2"], equal_to("2023-08-10 10:00:00"))
    assert_that(service.current_game['players_out'], has_key("member1"))
    assert_that(service.current_game['players_out']["member1"], is_not(None))
    assert_that(service.current_game['players_out'], has_key("member2"))
    assert_that(service.current_game['players_out']["member2"], equal_to(None))
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 1)
def test_remove_player_not_in():
    service = set_up()
    service.players = ["member2"]
    service.current_game["game_id"] = 1
    service.current_game['players'] = {"member2": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member2": None}
    service.remove_player("member1")
    assert_that(service.players, equal_to(["member2"]))
    assert_that(service.current_game['players'], is_not(has_key("member1")))
    assert_that(service.current_game['players'], has_key("member2"))
    assert_that(service.current_game['players']["member2"], equal_to("2023-08-10 10:00:00"))
    assert_that(service.current_game['players_out'], is_not(has_key("member1")))
    assert_that(service.current_game['players_out'], has_key("member2"))
    assert_that(service.current_game['players_out']["member2"], equal_to(None))
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 2)
@patch("pururu.config.ATTENDANCE_CHECK_DELAY", 1000)
def test_remove_player_emit_intent():
    service = set_up()
    service.players = ["member1", "member2"]
    service.current_game["game_id"] = 1
    service.current_game['players'] = {"member1": "2023-08-10 10:00:00", "member2": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member1": None, "member2": None}
    service.remove_player("member1")
    event_type, event, delay = service.event_system.emit_event_with_delay.call_args[0]
    assert_that(event_type, equal_to(EventType.END_GAME_INTENT))
    assert_that(type(event), equal_to(EndGameIntentEvent))
    assert_that(event.game_id, equal_to(1))
    assert_that(event.players, equal_to(["member2"]))
    assert_that(delay, equal_to(1000))
    service.event_system.emit_event_with_delay.assert_called_once()
    service.event_system.emit_event.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
def test_register_new_game_not_enough_players():
    service = set_up()
    service.players = ["member1", "member2"]
    service.current_game["game_id"] = None
    service.current_game['players'] = {"member1": "2023-08-10 10:00:00", "member2": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member1": None, "member2": None}
    service.register_new_game()
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 1)
def test_register_new_game_already_a_game_going():
    service = set_up()
    service.current_game["game_id"] = 1
    service.players = ["member1", "member2"]
    service.current_game["game_id"] = None
    service.current_game['players'] = {"member1": "2023-08-10 10:00:00", "member2": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member1": None, "member2": None}
    service.register_new_game()
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 1)
@patch("pururu.utils.get_current_time_formatted", return_value="curr_date")
@pytest.mark.usefixtures("attendance")
def test_register_new_game_ok(utils_mock, attendance: Attendance):
    service = set_up()
    service.players = ["member1", "member2"]
    service.current_game['players'] = {"member1": "2023-08-10 10:00:00", "member2": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member1": None, "member2": None}
    service.database_service.get_last_attendance.return_value = attendance
    service.register_new_game()
    assert_that(service.current_game["game_id"], equal_to(attendance.game_id + 1))
    assert_that(service.current_game['players'], equal_to({"member1": "curr_date", "member2": "curr_date"}))
    assert_that(service.current_game['players_out'], equal_to({}))
    event_type, event = service.event_system.emit_event.call_args[0]
    assert_that(event_type, equal_to(EventType.GAME_STARTED))
    assert_that(type(event), equal_to(GameStartedEvent))
    assert_that(event.game_id, equal_to(attendance.game_id + 1))
    assert_that(event.players, equal_to(["member1", "member2"]))
    service.event_system.emit_event.assert_called_once()
    service.database_service.get_last_attendance.assert_called_once()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 2)
def test_end_game_there_are_still_players():
    service = set_up()
    service.players = ["member1", "member2"]
    service.current_game["game_id"] = 1
    service.current_game['players'] = {"member1": "2023-08-10 10:00:00", "member2": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member1": None, "member2": None}
    service.end_game()
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 5)
def test_end_game_no_current_game():
    service = set_up()
    service.players = ["member1", "member2"]
    service.current_game['players'] = {"member1": "2023-08-10 10:00:00", "member2": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member1": None, "member2": None}
    service.end_game()
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
@patch("pururu.config.PLAYERS", ["member1", "member2", "member3", "member4"])
@patch("pururu.config.MIN_ATTENDANCE_TIME", 60)
@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10 10:00:00")
@freeze_time("2023-08-10 10:10:00")
def test_end_game_not_enough_player_attendance(utils_mock):
    service = set_up()
    service.players = ["member1", "member2"]
    service.current_game["game_id"] = 1
    service.current_game['players'] = {"member1": "2023-08-10 10:00:00", "member2": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member1": "2023-08-10 10:00:30", "member2": None}
    service.end_game()
    service.event_system.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
@patch("pururu.config.PLAYERS", ["member1", "member2", "member3", "member4"])
@patch("pururu.config.MIN_ATTENDANCE_TIME", 60)
@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10 10:00:00")
@freeze_time("2023-08-10 10:10:00")
def test_end_game_ok(utils_mock):
    service = set_up()
    service.players = ["member1", "member2"]
    service.current_game["game_id"] = 1
    service.current_game['players'] = {"member1": "2023-08-10 10:00:00", "member2": "2023-08-10 10:00:00",
                                       "member3": "2023-08-10 10:00:00"}
    service.current_game['players_out'] = {"member1": None, "member2": None, "member3": "2023-08-10 10:09:30"}
    service.end_game()
    event_type, event = service.event_system.emit_event.call_args[0]
    assert_that(event_type, equal_to(EventType.GAME_ENDED))
    assert_that(type(event), equal_to(GameEndedEvent))
    assert_that(event.attendance.game_id, equal_to(1))
    assert_that(event.attendance.date, equal_to("2023-08-10 10:00:00"))
    assert_that(event.attendance.description, equal_to("Game"))
    assert_that(event.attendance.members[0].member, equal_to("member1"))
    assert_that(event.attendance.members[0].attendance, equal_to(True))
    assert_that(event.attendance.members[0].justified, equal_to(True))
    assert_that(event.attendance.members[0].motive, equal_to(""))
    assert_that(event.attendance.members[1].member, equal_to("member2"))
    assert_that(event.attendance.members[1].attendance, equal_to(True))
    assert_that(event.attendance.members[1].justified, equal_to(True))
    assert_that(event.attendance.members[1].motive, equal_to(""))
    assert_that(event.attendance.members[2].member, equal_to("member3"))
    assert_that(event.attendance.members[2].attendance, equal_to(True))
    assert_that(event.attendance.members[2].justified, equal_to(True))
    assert_that(event.attendance.members[2].motive, equal_to(""))
    assert_that(event.attendance.members[3].member, equal_to("member4"))
    assert_that(event.attendance.members[3].attendance, equal_to(False))
    assert_that(event.attendance.members[3].justified, equal_to(False))
    assert_that(event.attendance.members[3].motive, equal_to(""))
    assert_that(service.database_service.insert_clocking.call_count, equal_to(3))
    service.event_system.emit_event.assert_called_once()
    service.database_service.upsert_attendance.assert_called_once()
