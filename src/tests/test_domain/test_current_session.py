from datetime import datetime
from unittest.mock import patch

from freezegun import freeze_time
from hamcrest import assert_that, equal_to, has_items, has_length

from pururu.domain.current_session import CurrentSession
from pururu.domain.entities import Poll
from tests.test_domain.test_entities import poll


@freeze_time("2023-08-10 10:00:00")
def test_clock_in_ok_use_default_time():
    # Given
    current_session = CurrentSession()
    # When
    current_session.clock_in("member1")
    # Then
    assert_that(current_session.online_players, equal_to({"member1"}))
    assert_that(current_session.players_clock_ins, equal_to({"member1": ["2023-08-10 10:00:00"]}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": []}))


def test_clock_in_ok_use_given_time():
    # Given
    current_session = CurrentSession()
    # When
    current_session.clock_in("member1", datetime(2023, 8, 10, 9))
    # Then
    assert_that(current_session.online_players, equal_to({"member1"}))
    assert_that(current_session.players_clock_ins, equal_to({"member1": ["2023-08-10 09:00:00"]}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": []}))


@freeze_time("2023-08-10 10:00:00")
def test_clock_in_second_clock_in():
    # Given
    current_session = CurrentSession()
    current_session.players_clock_ins = {"member1": ["2023-08-10 09:00:00"]}
    current_session.players_clock_outs = {"member1": ["2023-08-10 09:45:00"]}
    # When
    current_session.clock_in("member1")
    # Then
    assert_that(current_session.online_players, equal_to({"member1"}))
    assert_that(current_session.players_clock_ins,
                equal_to({"member1": ["2023-08-10 09:00:00", "2023-08-10 10:00:00"]}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": ["2023-08-10 09:45:00"]}))


@freeze_time("2023-08-10 10:00:00")
def test_clock_in_already_online():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1"}
    current_session.players_clock_ins = {"member1": ["2023-08-10 09:00:00"]}
    current_session.players_clock_outs = {"member1": []}
    # When
    current_session.clock_in("member1")
    # Then
    assert_that(current_session.online_players, equal_to({"member1"}))
    assert_that(current_session.players_clock_ins, equal_to({"member1": ["2023-08-10 09:00:00"]}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": []}))


@freeze_time("2023-08-10 10:00:00")
def test_clock_out_ok_use_default_time():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1"}
    current_session.players_clock_ins = {"member1": ["2023-08-10 09:00:00"]}
    current_session.players_clock_outs = {"member1": []}
    # When
    current_session.clock_out("member1")
    # Then
    assert_that(current_session.online_players, equal_to(set()))
    assert_that(current_session.players_clock_ins, equal_to({"member1": ["2023-08-10 09:00:00"]}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": ["2023-08-10 10:00:00"]}))


def test_clock_out_ok_use_given_time():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1"}
    current_session.players_clock_ins = {"member1": ["2023-08-10 09:00:00"]}
    current_session.players_clock_outs = {"member1": []}
    # When
    current_session.clock_out("member1", datetime(2023, 8, 10, 9, 45))
    # Then
    assert_that(current_session.online_players, equal_to(set()))
    assert_that(current_session.players_clock_ins, equal_to({"member1": ["2023-08-10 09:00:00"]}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": ["2023-08-10 09:45:00"]}))


def test_clock_out_player_not_online():
    # Given
    current_session = CurrentSession()
    current_session.players_clock_ins = {"member1": ["2023-08-10 09:00:00"]}
    current_session.players_clock_outs = {"member1": ["2023-08-10 09:45:00"]}
    # When
    current_session.clock_out("member1")
    # Then
    assert_that(current_session.online_players, equal_to(set()))
    assert_that(current_session.players_clock_ins, equal_to({"member1": ["2023-08-10 09:00:00"]}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": ["2023-08-10 09:45:00"]}))


def test_clock_out_player_not_in_clock_out():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1"}
    current_session.players_clock_ins = {}
    current_session.players_clock_outs = {}
    # When
    current_session.clock_out("member1")
    # Then
    assert_that(current_session.online_players, equal_to(set()))
    assert_that(current_session.players_clock_ins, equal_to({}))
    assert_that(current_session.players_clock_outs, equal_to({}))


def test_get_player_time_ok():
    # Given
    current_session = CurrentSession()
    current_session.players_clock_ins = {"member1": ["2023-08-10 09:00:00", "2023-08-10 09:30:00"]}
    current_session.players_clock_outs = {"member1": ["2023-08-10 09:15:00", "2023-08-10 10:00:00"]}
    expected_player_time = 2700  # 15 min + 30 min = 45 min = 2700 sec
    # When
    actual_player_time = current_session.get_player_time("member1")
    # Then
    assert_that(actual_player_time, equal_to(expected_player_time))


@freeze_time("2023-08-10 10:00:00")
def test_get_player_time_ok_while_still_online():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1"}
    current_session.players_clock_ins = {"member1": ["2023-08-10 09:30:00"]}
    current_session.players_clock_outs = {"member1": []}
    expected_player_time = 1800  # 30 min
    # When
    actual_player_time = current_session.get_player_time("member1")
    # Then
    assert_that(actual_player_time, equal_to(expected_player_time))


def test_get_player_time_no_player_data():
    # Given
    current_session = CurrentSession()
    expected_player_time = 0
    # When
    actual_player_time = current_session.get_player_time("member1")
    # Then
    assert_that(actual_player_time, equal_to(expected_player_time))


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 2)
def test_should_start_new_game_true():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1", "member2"}
    current_session.game_id = None
    # When
    actual_should_start_new_game = current_session.should_start_new_game()
    # Then
    assert_that(actual_should_start_new_game, equal_to(True))


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 2)
def test_should_start_new_game_false_game_already_going():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1", "member2"}
    current_session.game_id = 1
    # When
    actual_should_start_new_game = current_session.should_start_new_game()
    # Then
    assert_that(actual_should_start_new_game, equal_to(False))


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
def test_should_start_new_game_false_not_enough_players():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1", "member2"}
    current_session.game_id = None
    # When
    actual_should_start_new_game = current_session.should_start_new_game()
    # Then
    assert_that(actual_should_start_new_game, equal_to(False))


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
def test_should_end_game_true():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1", "member2"}
    current_session.game_id = 1
    # When
    actual_should_end_game = current_session.should_end_game()
    # Then
    assert_that(actual_should_end_game, equal_to(True))


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
def test_should_end_game_false_theres_no_game():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1", "member2"}
    current_session.game_id = None
    # When
    actual_should_end_game = current_session.should_end_game()
    # Then
    assert_that(actual_should_end_game, equal_to(False))


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 1)
def test_should_end_game_false_too_many_players():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1", "member2"}
    current_session.game_id = 1
    # When
    actual_should_end_game = current_session.should_end_game()
    # Then
    assert_that(actual_should_end_game, equal_to(False))


def test_get_players():
    # Given
    current_session = CurrentSession()
    current_session.online_players = {"member1", "member2"}
    # When
    actual_players = current_session.get_players()
    # Then
    assert_that(actual_players, has_items("member1", "member2"))


def test_str():
    # Given
    current_session = CurrentSession()
    current_session.game_id = 1
    current_session.online_players = {"member1"}
    current_session.players_clock_ins = {"member1": ["2023-08-10 09:00:00"]}
    current_session.players_clock_outs = {"member1": ["2023-08-10 09:45:00"]}
    expected_str = ("Game 1, players {'member1'}, clock_ins {'member1': ['2023-08-10 09:00:00']}, "
                    "clock_outs {'member1': ['2023-08-10 09:45:00']}")
    # When
    actual_str = str(current_session)
    # Then
    assert_that(actual_str, equal_to(expected_str))


def test_reset():
    # Given
    current_session = CurrentSession()
    current_session.game_id = 1
    current_session.online_players = {"member1"}
    current_session.players_clock_ins = {"member1": ["2023-08-10 09:00:00"]}
    current_session.players_clock_outs = {"member1": ["2023-08-10 09:45:00"]}
    current_session.polls = {1: {"foo": "bar"}}
    # When
    current_session.reset()
    # Then
    assert_that(current_session.game_id, equal_to(None))
    assert_that(current_session.online_players, equal_to(set()))
    assert_that(current_session.players_clock_ins, equal_to({}))
    assert_that(current_session.players_clock_outs, equal_to({}))
    assert_that(current_session.polls, equal_to({1: {"foo": "bar"}}))


def test_adjust_players_clocking_start_time_period_fully_in_the_past():
    # Given
    current_session = CurrentSession()
    current_session.players_clock_ins = {"member1": ["2023-08-10 08:30:00"]}
    current_session.players_clock_outs = {"member1": ["2023-08-10 08:40:00"]}
    # When
    current_session.adjust_players_clocking_start_time(start_time=datetime(2023, 8, 10, 9))
    # Then
    assert_that(current_session.players_clock_ins, equal_to({"member1": []}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": []}))


def test_adjust_players_clocking_start_time_period_partial_in_the_past():
    # Given
    current_session = CurrentSession()
    current_session.players_clock_ins = {"member1": ["2023-08-10 08:30:00"]}
    current_session.players_clock_outs = {"member1": ["2023-08-10 09:45:00"]}
    # When
    current_session.adjust_players_clocking_start_time(start_time=datetime(2023, 8, 10, 9))
    # Then
    assert_that(current_session.players_clock_ins, equal_to({"member1": ["2023-08-10 09:00:00"]}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": ["2023-08-10 09:45:00"]}))


def test_adjust_players_clocking_start_time_period_in_range():
    # Given
    current_session = CurrentSession()
    current_session.players_clock_ins = {"member1": ["2023-08-10 09:00:00", "2023-08-10 09:50:00"]}
    current_session.players_clock_outs = {"member1": ["2023-08-10 09:45:00"]}
    # When
    current_session.adjust_players_clocking_start_time(start_time=datetime(2023, 8, 10, 9))
    # Then
    assert_that(current_session.players_clock_ins,
                equal_to({"member1": ["2023-08-10 09:00:00", "2023-08-10 09:50:00"]}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": ["2023-08-10 09:45:00"]}))


def test_adjust_players_clocking_end_time_period_fully_in_the_future():
    # Given
    current_session = CurrentSession()
    current_session.players_clock_ins = {"member1": ["2023-08-10 09:30:00"]}
    current_session.players_clock_outs = {"member1": ["2023-08-10 09:45:00"]}
    # When
    current_session.adjust_players_clocking_end_time(end_time=datetime(2023, 8, 10, 9))
    # Then
    assert_that(current_session.players_clock_ins, equal_to({"member1": []}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": []}))


def test_adjust_players_clocking_end_time_period_partial_in_the_future():
    # Given
    current_session = CurrentSession()
    current_session.players_clock_ins = {"member1": ["2023-08-10 08:30:00"]}
    current_session.players_clock_outs = {"member1": ["2023-08-10 09:45:00"]}
    # When
    current_session.adjust_players_clocking_end_time(end_time=datetime(2023, 8, 10, 9))
    # Then
    assert_that(current_session.players_clock_ins, equal_to({"member1": ["2023-08-10 08:30:00"]}))
    assert_that(current_session.players_clock_outs, equal_to({"member1": ["2023-08-10 09:00:00"]}))


def test_adjust_players_clocking_end_time_period_in_range():
    # Given
    current_session = CurrentSession()
    current_session.players_clock_ins = {"member1": ["2023-08-10 08:00:00", "2023-08-10 08:50:00"]}
    current_session.players_clock_outs = {"member1": ["2023-08-10 08:45:00"]}
    # When
    current_session.adjust_players_clocking_end_time(end_time=datetime(2023, 8, 10, 9))
    # Then
    assert_that(current_session.players_clock_ins,
                equal_to({"member1": ["2023-08-10 08:00:00", "2023-08-10 08:50:00"]}))
    assert_that(current_session.players_clock_outs,
                equal_to({"member1": ["2023-08-10 08:45:00", "2023-08-10 09:00:00"]}))


def test_add_new_poll_ok(poll: Poll):
    # Given
    current_session = CurrentSession()
    # When
    current_session.add_new_poll(poll)
    # Then
    assert_that(current_session.polls, has_length(1))
    assert_that(current_session.polls[poll.message_id],
                equal_to({'channel_id': poll.channel_id, "expires_at": poll.expires_at,
                          "resolution": poll.resolution_type}))


def test_remove_poll_ok(poll: Poll):
    # Given
    current_session = CurrentSession()
    current_session.polls[poll.message_id] = {'channel_id': poll.channel_id, "expires_at": poll.expires_at,
                                              "resolution": poll.resolution_type}
    current_session.polls[poll.message_id + 1] = {'channel_id': poll.channel_id, "expires_at": poll.expires_at,
                                                  "resolution": poll.resolution_type}
    # When
    current_session.remove_poll(poll.message_id)
    # Then
    assert_that(current_session.polls, has_length(1))


@freeze_time("2023-08-10 10:00:00")
def test_get_expired_polls_ok(poll: Poll):
    # Given
    current_session = CurrentSession()
    current_session.polls[poll.message_id] = {'channel_id': poll.channel_id, "expires_at": datetime(2023, 8, 10, 9),
                                              "resolution": poll.resolution_type}
    current_session.polls[poll.message_id + 1] = {'channel_id': poll.channel_id,
                                                  "expires_at": datetime(2023, 8, 10, 11),
                                                  "resolution": poll.resolution_type}
    # When
    expired_polls = current_session.get_expired_polls()
    # Then
    assert_that(expired_polls, has_length(1))
    assert_that(expired_polls[0].message_id, equal_to(poll.message_id))
    assert_that(expired_polls[0].channel_id, equal_to(poll.channel_id))
    assert_that(expired_polls[0].resolution_type, equal_to(poll.resolution_type))
