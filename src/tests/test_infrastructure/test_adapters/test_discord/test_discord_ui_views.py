from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

import discord
import pytest
from hamcrest import assert_that, equal_to, is_, not_none, instance_of

from pururu.domain.entities.session import Session, Status, Type, PlayerSession, Interval
from pururu.infrastructure.adapters.discord.discord_ui_views import (
    SessionInfoLayoutView,
    EditSessionTypeModal,
    EditAttendanceModal,
    RepairAttendanceModal,
)


# ------------------------------
# FIXTURES
# ------------------------------

@pytest.fixture
def mock_session_draft():
    """Create a mock draft session for testing"""
    session = Mock(spec=Session)
    session.id = "test_session_id"
    session.season_id = "test_season_id"
    session.status = Status.DRAFT
    session.type = Type.OFFICIAL_GAME
    session.start_time = datetime.now()
    session.end_time = None
    
    player1 = Mock(spec=PlayerSession)
    player1.player_id = "123456"
    player1.attended = True
    player1.justified_absence = False
    player1.motive = ""
    player1.intervals = [Interval(start=datetime.now())]
    
    session.players = [player1]
    session.get_checked_in_players = Mock(return_value=[player1])
    session.get_first_joiner = Mock(return_value=player1)
    session.get_offline_players = Mock(return_value=[])
    session.get_absent_players = Mock(return_value=[])
    session.is_concluded = Mock(return_value=False)
    
    return session


@pytest.fixture
def mock_session_completed():
    """Create a mock completed session for testing"""
    session = Mock(spec=Session)
    session.id = "test_session_id"
    session.season_id = "test_season_id"
    session.status = Status.COMPLETED
    session.type = Type.OFFICIAL_GAME
    session.start_time = datetime.now() - timedelta(hours=2)
    session.end_time = datetime.now()
    
    player1 = Mock(spec=PlayerSession)
    player1.player_id = "123456"
    player1.attended = False
    player1.justified_absence = True
    player1.motive = "Had a meeting"
    
    player2 = Mock(spec=PlayerSession)
    player2.player_id = "789012"
    player2.attended = False
    player2.justified_absence = False
    player2.motive = ""
    
    session.players = [player1, player2]
    session.get_checked_in_players = Mock(return_value=[])
    session.get_offline_players = Mock(return_value=[])
    session.get_absent_players = Mock(return_value=[player1, player2])
    session.is_concluded = Mock(return_value=True)
    
    return session


@pytest.fixture
def mock_callbacks():
    """Create mock callback functions"""
    return {
        'on_session_type_change': Mock(),
        'on_attendance_edit': Mock(),
        'on_attendance_repair': Mock(),
    }


# ------------------------------
# SessionInfoLayoutView TESTS
# ------------------------------

@pytest.mark.unit
def test_session_info_layout_view_accent_color_draft(mock_session_draft, mock_callbacks):
    """Test SessionInfoLayoutView returns correct accent color for draft status"""
    # Arrange
    with patch.object(SessionInfoLayoutView, '__init__', lambda self, **kwargs: None):
        view = SessionInfoLayoutView()
        view.session = mock_session_draft
    
    # Act
    color = view.get_accent_color_from_status()
    
    # Assert
    assert_that(color, equal_to(discord.Color.blue()))


@pytest.mark.unit
def test_session_info_layout_view_accent_color_completed(mock_session_completed, mock_callbacks):
    """Test SessionInfoLayoutView returns correct accent color for completed status"""
    # Arrange
    with patch.object(SessionInfoLayoutView, '__init__', lambda self, **kwargs: None):
        view = SessionInfoLayoutView()
        view.session = mock_session_completed
    
    # Act
    color = view.get_accent_color_from_status()
    
    # Assert
    assert_that(color, equal_to(discord.Color.green()))


@pytest.mark.unit
def test_session_info_layout_view_accent_color_discarded(mock_callbacks):
    """Test SessionInfoLayoutView returns correct accent color for discarded status"""
    # Arrange
    session = Mock(spec=Session)
    session.status = Status.DISCARDED
    
    with patch.object(SessionInfoLayoutView, '__init__', lambda self, **kwargs: None):
        view = SessionInfoLayoutView()
        view.session = session
    
    # Act
    color = view.get_accent_color_from_status()
    
    # Assert
    assert_that(color, equal_to(discord.Color.red()))


@pytest.mark.unit
def test_session_info_layout_view_accent_color_unknown():
    """Test SessionInfoLayoutView returns yellow color for unknown status"""
    # Arrange
    session = Mock(spec=Session)
    session.status = "UNKNOWN_STATUS"  # Some unknown status
    
    with patch.object(SessionInfoLayoutView, '__init__', lambda self, **kwargs: None):
        view = SessionInfoLayoutView()
        view.session = session
    
    # Act
    color = view.get_accent_color_from_status()
    
    # Assert
    assert_that(color, equal_to(discord.Color.yellow()))


# ------------------------------
# EditSessionTypeModal TESTS
# ------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_edit_session_type_modal_on_submit_calls_callback(mock_session_draft, mock_callbacks):
    """Test EditSessionTypeModal on_submit calls callback with correct parameters"""
    # Arrange
    with patch.object(EditSessionTypeModal, '__init__', lambda self, **kwargs: None):
        modal = EditSessionTypeModal()
        modal.session = mock_session_draft
        modal.callback = mock_callbacks['on_session_type_change']
        
        # Mock the selector component
        mock_selector = Mock()
        mock_selector.component = Mock()
        mock_selector.component.values = ["Additional Game"]
        modal.selector = mock_selector
        
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.response.send_message = AsyncMock()
    
    # Act
    await modal.on_submit(mock_interaction)
    
    # Assert
    mock_callbacks['on_session_type_change'].assert_called_once_with("test_session_id", "Additional Game")
    mock_interaction.response.send_message.assert_called_once()


# ------------------------------
# EditAttendanceModal TESTS
# ------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_edit_attendance_modal_on_submit_calls_callback(mock_session_completed, mock_callbacks):
    """Test EditAttendanceModal on_submit calls callback with correct parameters"""
    # Arrange
    with patch.object(EditAttendanceModal, '__init__', lambda self, **kwargs: None):
        modal = EditAttendanceModal()
        modal.session = mock_session_completed
        modal.callback = mock_callbacks['on_attendance_edit']
        
        # Mock the user selector
        mock_user = Mock()
        mock_user.id = 123456
        
        mock_justify_selector = Mock()
        mock_justify_selector.component = Mock()
        mock_justify_selector.component.values = [mock_user]
        modal.justify_user_selector = mock_justify_selector
        modal.user_motive_dict = {}
        
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.response.send_message = AsyncMock()
    
    # Act
    await modal.on_submit(mock_interaction)
    
    # Assert
    assert_that(mock_callbacks['on_attendance_edit'].called, is_(True))
    call_args = mock_callbacks['on_attendance_edit'].call_args[0]
    assert_that(call_args[0], equal_to("test_session_id"))
    assert_that(call_args[1], instance_of(dict))  # justification_dict
    assert_that(call_args[2], instance_of(dict))  # motives_dict
    mock_interaction.response.send_message.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_repair_attendance_modal_only_submits_absent_players(mock_session_completed, mock_callbacks):
    with patch.object(RepairAttendanceModal, '__init__', lambda self, **kwargs: None):
        modal = RepairAttendanceModal()
        modal.session = mock_session_completed
        modal.callback = mock_callbacks['on_attendance_repair']
        modal.absent_player_ids = {"123456", "789012"}
        selected_absent = Mock(id=123456)
        selected_untracked = Mock(id=999999)
        modal.player_selector = Mock()
        modal.player_selector.component.values = [selected_absent, selected_untracked]
        interaction = Mock(spec=discord.Interaction)
        interaction.response.send_message = AsyncMock()

    await modal.on_submit(interaction)

    mock_callbacks['on_attendance_repair'].assert_called_once_with("test_session_id", ["123456"])
    interaction.response.send_message.assert_awaited_once()


# ------------------------------
# Import and Class Existence TESTS
# ------------------------------

@pytest.mark.unit
def test_session_info_layout_view_class_exists():
    """Test that SessionInfoLayoutView class can be imported and exists"""
    # Assert
    assert_that(SessionInfoLayoutView, is_(not_none()))
    assert_that(callable(SessionInfoLayoutView), is_(True))


@pytest.mark.unit
def test_edit_session_type_modal_class_exists():
    """Test that EditSessionTypeModal class can be imported and exists"""
    # Assert
    assert_that(EditSessionTypeModal, is_(not_none()))
    assert_that(callable(EditSessionTypeModal), is_(True))


@pytest.mark.unit
def test_edit_attendance_modal_class_exists():
    """Test that EditAttendanceModal class can be imported and exists"""
    # Assert
    assert_that(EditAttendanceModal, is_(not_none()))
    assert_that(callable(EditAttendanceModal), is_(True))


@pytest.mark.unit
def test_repair_attendance_modal_class_exists():
    assert_that(RepairAttendanceModal, is_(not_none()))
    assert_that(callable(RepairAttendanceModal), is_(True))


@pytest.mark.unit
def test_view_classes_have_required_attributes():
    """Test that view classes have expected attributes"""
    # Assert
    assert_that(hasattr(SessionInfoLayoutView, 'get_accent_color_from_status'), is_(True))
    assert_that(hasattr(EditSessionTypeModal, 'on_submit'), is_(True))
    assert_that(hasattr(EditAttendanceModal, 'on_submit'), is_(True))
    assert_that(hasattr(RepairAttendanceModal, 'on_submit'), is_(True))
