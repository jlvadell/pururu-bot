from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, equal_to, instance_of

from pururu.domain.entities.session import Session, Type
from pururu.infrastructure.adapters.google_sheets.entities import AttendanceSheet, ClockingSheet
from pururu.infrastructure.adapters.google_sheets.mapper import GoogleSheetsMapper


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    with patch('pururu.infrastructure.adapters.google_sheets.mapper.settings') as mock:
        mock.google_sheets.general.player_order.get = MagicMock(
            side_effect=lambda x, default: {"player1": 0, "player2": 1}.get(x, default))
        mock.general.min_attendance_time = 300
        mock.general.min_attendance_members = 2
        yield mock


@pytest.fixture
def mock_session():
    """Create a mock session"""
    session = MagicMock(spec=Session)
    session.id = "session123"
    session.type = Type.OFFICIAL_GAME

    # Mock player sessions
    player1 = MagicMock()
    player1.player_id = "player1"
    player1.attended = True
    player1.justified_absence = False
    player1.motive = ""
    player1.get_total_time.return_value = 600

    player2 = MagicMock()
    player2.player_id = "player2"
    player2.attended = False
    player2.justified_absence = True
    player2.motive = "sick"
    player2.get_total_time.return_value = 0

    session.players = [player1, player2]
    session.get_official_start_time.return_value = datetime(2025, 10, 1, 10, 0, 0, 123)
    session.get_official_end_time.return_value = datetime(2025, 10, 1, 12, 0, 0)

    return session


@pytest.mark.unit
def test_to_attendance(mock_settings, mock_session):
    """Test converting Session to AttendanceSheet"""
    # Act
    result = GoogleSheetsMapper.to_attendance(mock_session)

    # Assert
    assert_that(result, instance_of(AttendanceSheet))
    assert_that(result.session_id, equal_to("session123"))
    assert_that(result.date, equal_to("2025-10-01 10:00:00"))
    assert_that(result.description, equal_to("Juegueo Oficial"))
    assert_that(len(result.absence), equal_to(2))
    assert_that(len(result.unjustified), equal_to(2))


@pytest.mark.unit
def test_to_attendance_absence_logic(mock_settings, mock_session):
    """Test to_attendance absence and unjustified logic"""
    # Act
    result = GoogleSheetsMapper.to_attendance(mock_session)

    # Assert
    # Player1 attended -> absence=FALSE
    assert_that(result.absence[0], equal_to("FALSE"))
    # Player2 did not attend -> absence=TRUE
    assert_that(result.absence[1], equal_to("TRUE"))

    # Player1 attended -> unjustified=FALSE
    assert_that(result.unjustified[0], equal_to("FALSE"))
    # Player2 did not attend but justified -> unjustified=FALSE
    assert_that(result.unjustified[1], equal_to("FALSE"))


@pytest.mark.unit
def test_to_attendance_unjustified_absence(mock_settings):
    """Test to_attendance with unjustified absence"""
    # Arrange
    session = MagicMock(spec=Session)
    session.id = "session123"
    session.type = Type.OFFICIAL_GAME

    player = MagicMock()
    player.player_id = "player1"
    player.attended = False
    player.justified_absence = False  # Not justified
    player.motive = ""

    session.players = [player]
    session.get_official_start_time.return_value = datetime(2025, 10, 1, 10, 0, 0)
    session.get_official_end_time.return_value = datetime(2025, 10, 1, 12, 0, 0)

    # Act
    result = GoogleSheetsMapper.to_attendance(session)

    # Assert
    assert_that(result.absence[0], equal_to("TRUE"))
    assert_that(result.unjustified[0], equal_to("TRUE"))


@pytest.mark.unit
def test_to_clocking(mock_settings, mock_session):
    """Test converting Session to ClockingSheet"""
    # Act
    result = GoogleSheetsMapper.to_clocking(mock_session, 42)

    # Assert
    assert_that(result, instance_of(ClockingSheet))
    assert_that(result.game_id, equal_to(42))
    assert_that(len(result.playtimes), equal_to(2))
    assert_that(result.playtimes[0], equal_to(600))
    assert_that(result.playtimes[1], equal_to(0))


@pytest.mark.unit
def test_to_clocking_player_ordering(mock_settings):
    """Test to_clocking respects player ordering"""
    # Arrange
    session = MagicMock(spec=Session)

    player1 = MagicMock()
    player1.player_id = "player1"
    player1.get_total_time.return_value = 100

    player2 = MagicMock()
    player2.player_id = "player2"
    player2.get_total_time.return_value = 200

    # Add in reverse order
    session.players = [player2, player1]
    session.get_official_start_time.return_value = datetime(2025, 10, 1, 10, 0, 0)
    session.get_official_end_time.return_value = datetime(2025, 10, 1, 12, 0, 0)

    # Act
    result = GoogleSheetsMapper.to_clocking(session, 1)

    # Assert - should be sorted by player_order
    assert_that(result.playtimes[0], equal_to(100))  # player1 first
    assert_that(result.playtimes[1], equal_to(200))  # player2 second


@pytest.mark.unit
def test_parse_bool_to_str_true():
    """Test _parse_bool_to_str with True"""
    # Act
    result = GoogleSheetsMapper._parse_bool_to_str(True)

    # Assert
    assert_that(result, equal_to("TRUE"))


@pytest.mark.unit
def test_parse_bool_to_str_false():
    """Test _parse_bool_to_str with False"""
    # Act
    result = GoogleSheetsMapper._parse_bool_to_str(False)

    # Assert
    assert_that(result, equal_to("FALSE"))


@pytest.mark.unit
def test_parse_type_from_str_official_game():
    """Test _parse_type_from_str for official game"""
    # Act
    result = GoogleSheetsMapper._parse_type_from_str("Juegueo Oficial")

    # Assert
    assert_that(result, equal_to(Type.OFFICIAL_GAME))


@pytest.mark.unit
def test_parse_type_from_str_additional_game():
    """Test _parse_type_from_str for additional game"""
    # Act
    result = GoogleSheetsMapper._parse_type_from_str("Juegueo Adicional Oficial")

    # Assert
    assert_that(result, equal_to(Type.ADDITIONAL_GAME))


@pytest.mark.unit
def test_parse_type_from_str_official_meeting():
    """Test _parse_type_from_str for official meeting"""
    # Act
    result = GoogleSheetsMapper._parse_type_from_str("Quedada Oficial")

    # Assert
    assert_that(result, equal_to(Type.OFFICIAL_MEETING))


@pytest.mark.unit
def test_parse_type_from_str_unknown_defaults_to_official_game():
    """Test _parse_type_from_str with unknown value defaults to OFFICIAL_GAME"""
    # Act
    result = GoogleSheetsMapper._parse_type_from_str("Unknown Type")

    # Assert
    assert_that(result, equal_to(Type.OFFICIAL_GAME))


@pytest.mark.unit
def test_parse_type_to_str_official_game():
    """Test _parse_type_to_str for OFFICIAL_GAME"""
    # Act
    result = GoogleSheetsMapper._parse_type_to_str(Type.OFFICIAL_GAME)

    # Assert
    assert_that(result, equal_to("Juegueo Oficial"))


@pytest.mark.unit
def test_parse_type_to_str_additional_game():
    """Test _parse_type_to_str for ADDITIONAL_GAME"""
    # Act
    result = GoogleSheetsMapper._parse_type_to_str(Type.ADDITIONAL_GAME)

    # Assert
    assert_that(result, equal_to("Juegueo Adicional Oficial"))


@pytest.mark.unit
def test_parse_type_to_str_official_meeting():
    """Test _parse_type_to_str for OFFICIAL_MEETING"""
    # Act
    result = GoogleSheetsMapper._parse_type_to_str(Type.OFFICIAL_MEETING)

    # Assert
    assert_that(result, equal_to("Quedada Oficial"))


@pytest.mark.unit
def test_parse_type_to_str_unknown_defaults():
    """Test _parse_type_to_str with unknown Type defaults to 'Juegueo Oficial'"""
    # Act
    result = GoogleSheetsMapper._parse_type_to_str(999)  # Invalid type

    # Assert
    assert_that(result, equal_to("Juegueo Oficial"))
