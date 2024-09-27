from datetime import datetime
from unittest.mock import patch

from hamcrest import assert_that, equal_to, calling, raises

from pururu.domain.entities import BotEvent, Attendance, MemberStats, AttendanceEventType, MemberAttendance, Clocking, \
    SessionInfo
from pururu.domain.exceptions import CannotStartNewGame, CannotEndGame, GameEndedWithoutPrecondition
from pururu.domain.services.pururu_service import PururuService
from tests.test_domain.test_entities import attendance, member_stats


@patch('pururu.domain.services.discord_service.DiscordInterface')
@patch('pururu.domain.services.database_service.DatabaseInterface')
@patch('pururu.domain.current_session.CurrentSession')
def set_up(current_session, db_mock, dc_mock) -> PururuService:
    """
    Set-ups an instance of PururuService for testing
    :return: PururuService loaded with mocks
    """
    service = PururuService(db_mock)
    service.set_discord_service(dc_mock)
    service.current_session = current_session
    return service


def test_get_session_info_ok():
    # Given
    service = set_up()
    service.current_session.game_id = 1
    service.current_session.get_players.return_value = ["member1", "member2"]
    expected = SessionInfo(game_id=1, players=["member1", "member2"])
    # When
    actual = service.get_session_info()
    # Then
    assert_that(actual.game_id, equal_to(expected.game_id))
    assert_that(actual.players, equal_to(expected.players))
    service.current_session.get_players.assert_called_once()


def test_calculate_player_stats_ok(member_stats: MemberStats):
    # Given
    service = set_up()
    attendances = [
        Attendance(game_id=1, members=[MemberAttendance(member_stats.member, False, True, "")],
                   date="2023-08-10", event_type=AttendanceEventType.OFFICIAL_GAME),
        Attendance(game_id=2, members=[MemberAttendance(member_stats.member, False, False, "")],
                   date="2023-08-11", event_type=AttendanceEventType.OFFICIAL_GAME),
        Attendance(game_id=3, members=[MemberAttendance(member_stats.member, True, True, "")],
                   date="2023-08-12", event_type=AttendanceEventType.OFFICIAL_GAME),
    ]
    service.database_service.get_all_attendances.return_value = attendances
    service.database_service.get_player_coins.return_value = member_stats.coins
    # When
    actual = service.calculate_player_stats(member_stats.member)
    # Then
    assert_that(actual.member, equal_to(member_stats.member))
    assert_that(actual.total_events, equal_to(member_stats.total_events))
    assert_that(actual.absences, equal_to(member_stats.absences))
    assert_that(actual.justifications, equal_to(member_stats.justifications))
    assert_that(actual.points, equal_to(member_stats.points))
    assert_that(actual.absent_events, equal_to(member_stats.absent_events))
    assert_that(actual.coins, equal_to(member_stats.coins))
    service.database_service.get_all_attendances.assert_called_once()
    service.database_service.get_player_coins.assert_called_once_with(member_stats.member)
    service.current_session.assert_not_called()


def test_register_bot_event():
    # Given
    service = set_up()
    event = BotEvent(
        event_type="event_type",
        date="2023-08-10",
        description="Bot event description"
    )
    # When
    service.register_bot_event(event)
    # Then
    service.database_service.insert_bot_event.assert_called_once_with(event)
    service.current_session.assert_not_called()


def test_radd_player_start_new_game_true():
    # Given
    service = set_up()
    service.current_session.should_start_new_game.return_value = True
    service.current_session.get_players.return_value = {"member1"}
    # When
    result = service.add_player("member1", datetime(2023, 8, 10, 10))
    # Then
    assert_that(result, equal_to(True))
    service.current_session.clock_in.assert_called_once_with("member1", datetime(2023, 8, 10, 10))
    service.database_service.assert_not_called()


def test_add_player_start_new_game_false():
    # Given
    service = set_up()
    service.current_session.should_start_new_game.return_value = False
    # When
    result = service.add_player("member1", datetime(2023, 8, 10, 10))
    # Then
    assert_that(result, equal_to(False))
    service.current_session.clock_in.assert_called_once_with("member1", datetime(2023, 8, 10, 10))
    service.database_service.assert_not_called()


def test_remove_player_end_game_true():
    # Given
    service = set_up()
    service.current_session.should_end_game.return_value = True
    # When
    result = service.remove_player("member1", datetime(2023, 8, 10, 10))
    # Then
    assert_that(result, equal_to(True))
    service.current_session.clock_out.assert_called_once_with("member1", datetime(2023, 8, 10, 10))
    service.database_service.assert_not_called()


def test_remove_player_end_game_false():
    # Given
    service = set_up()
    service.current_session.should_end_game.return_value = False
    # When
    result = service.remove_player("member1", datetime(2023, 8, 10, 10))
    # Then
    assert_that(result, equal_to(False))
    service.current_session.clock_out.assert_called_once_with("member1", datetime(2023, 8, 10, 10))
    service.database_service.assert_not_called()


def test_start_new_game_conditions_not_met():
    # Given
    service = set_up()
    service.current_session.should_start_new_game.return_value = False
    # When-Then
    assert_that(calling(service.start_new_game)
                .with_args(datetime(2023, 8, 10, 10)), raises(CannotStartNewGame))
    service.current_session.assert_not_called()
    service.database_service.assert_not_called()


def test_start_new_game_ok(attendance: Attendance):
    # Given
    service = set_up()
    service.current_session.should_start_new_game.return_value = True
    service.database_service.get_last_attendance.return_value = attendance
    service.current_session.get_players.return_value = ["member1"]
    start_time = datetime(2023, 8, 10, 10)
    expected_game_id = attendance.game_id + 1
    # When
    result = service.start_new_game(start_time)
    # Then
    assert_that(result.game_id, equal_to(expected_game_id))
    assert_that(result.players, equal_to(["member1"]))
    service.database_service.get_last_attendance.assert_called_once()
    service.current_session.adjust_players_clocking_start_time.assert_called_once_with(start_time)


def test_end_game_conditions_not_met():
    # Given
    service = set_up()
    service.current_session.should_end_game.return_value = False
    # When-Then
    assert_that(calling(service.end_game)
                .with_args(datetime(2023, 8, 10, 10)), raises(CannotEndGame))
    service.current_session.assert_not_called()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
@patch("pururu.config.PLAYERS", ["member1", "member2", "member3", "member4"])
@patch("pururu.config.MIN_ATTENDANCE_TIME", 60)
@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10 10:00:00")
def test_end_game_not_enough_player_attendance(utils_mock):
    # Given
    service = set_up()
    service.current_session.get_player_time.side_effect = lambda player: \
        {"member1": 100, "member2": 20, "member3": 30, "member4": 50}[player]
    # When-Then
    assert_that(calling(service.end_game)
                .with_args(datetime(2023, 8, 10, 10, 0, 20)), raises(GameEndedWithoutPrecondition))
    service.current_session.reset.assert_called_once()
    service.database_service.assert_not_called()


@patch("pururu.config.MIN_ATTENDANCE_MEMBERS", 3)
@patch("pururu.config.PLAYERS", ["member1", "member2", "member3", "member4"])
@patch("pururu.config.MIN_ATTENDANCE_TIME", 60)
@patch("pururu.utils.get_current_time_formatted", return_value="2023-08-10")
def test_end_game_ok(utils_mock):
    # Given
    service = set_up()
    service.current_session.get_player_time.side_effect = lambda player: \
        {"member1": 300, "member2": 100, "member3": 200, "member4": 0}[player]
    service.current_session.game_id = 1
    expected_attendance = Attendance(
        game_id=1,
        members=[
            MemberAttendance("member1", True, True, ""),
            MemberAttendance("member2", True, True, ""),
            MemberAttendance("member3", True, True, ""),
            MemberAttendance("member4", False, False, ""),
        ],
        date="2023-08-10",
        event_type=AttendanceEventType.OFFICIAL_GAME,
    )
    expected_clocking = Clocking(
        game_id=1,
        playtimes=[300, 100, 200, 0],
    )
    # When
    result = service.end_game(datetime(2023, 8, 10, 10, 10))
    # Then
    __verify_attendance(result, expected_attendance)
    actual_clocking = service.database_service.upsert_clocking.call_args[0][0]
    actual_attendance = service.database_service.upsert_attendance.call_args[0][0]
    __verify_attendance(actual_attendance, expected_attendance)
    __verify_clocking(actual_clocking, expected_clocking)
    service.database_service.upsert_clocking.assert_called_once()
    service.database_service.upsert_attendance.assert_called_once()
    service.current_session.reset.assert_called_once()


def __verify_attendance(actual: Attendance, expected: Attendance):
    assert_that(actual.game_id, equal_to(expected.game_id))
    assert_that(actual.date, equal_to(expected.date))
    assert_that(actual.event_type, equal_to(expected.event_type))
    for actual_member, expected_member in zip(actual.members, expected.members):
        assert_that(actual_member.member, equal_to(expected_member.member))
        assert_that(actual_member.attendance, equal_to(expected_member.attendance))
        assert_that(actual_member.justified, equal_to(expected_member.justified))
        assert_that(actual_member.motive, equal_to(expected_member.motive))


def __verify_clocking(actual: Clocking, expected: Clocking):
    assert_that(actual.game_id, equal_to(expected.game_id))
    assert_that(actual.playtimes, equal_to(expected.playtimes))
