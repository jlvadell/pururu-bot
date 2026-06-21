from datetime import datetime
from unittest.mock import Mock, MagicMock, AsyncMock

import discord
import pytest
from hamcrest import assert_that, equal_to, is_, not_none, instance_of

from pururu.domain.entities.session import Session, Status, Type
from pururu.infrastructure.adapters.discord.discord_ui_components import (
    SessionStatusTitleTextDisplay,
    SessionDetailsTextDisplay,
    EditAttendanceButton,
    ChangeSessionTypeButton,
    NotifyMissingUsersButton,
    SessionTypeSelectorLabel,
    SessionTypeSelector,
    UserSelectorLabel,
    MotiveTextInput
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "status,expected_content",
    [
        (Status.DRAFT, "## Nueva sesión iniciada! :new:"),
        (Status.COMPLETED, "## Sesión concluida! :checkered_flag:"),
        (Status.DISCARDED, "## Sesión descartada! :x:"),
    ]
)
def test_session_status_title_text_display(status, expected_content):
    """Test SessionStatusTitleTextDisplay with various statuses"""
    # Act
    display = SessionStatusTitleTextDisplay(status=status)
    # Assert
    assert_that(display, is_(not_none()))
    assert_that(display.content, equal_to(expected_content))


@pytest.mark.unit
def test_session_details_text_display_ongoing():
    """Test SessionDetailsTextDisplay with ongoing session"""
    # Arrange
    mock_session = MagicMock(spec=Session)
    mock_session.type = Mock(value="session_value_data")
    mock_session.start_time = datetime(2025, 1, 1, 10, 0, 0)
    mock_session.is_concluded = Mock(return_value=False)
    mock_session.get_checked_in_players = Mock(return_value=[Mock(), Mock()])
    mock_session.get_first_joiner = Mock(return_value=Mock(player_id="123456"))
    # Act
    display = SessionDetailsTextDisplay(session=mock_session)

    # Assert
    assert_that(display, is_(not_none()))
    assert_that(display.content, equal_to(
        f":video_game: **Type:** `session_value_data`\n\n"
        f":busts_in_silhouette: **Players:** 2 / 5\n\n"
        f":clock3: **Started:** <t:{int(datetime(2025, 1, 1, 10, 0, 0).timestamp())}:f>\n\n"
        f":athletic_shoe: **Pole:** <@123456>\n\n"
    ))


@pytest.mark.unit
def test_session_details_text_display_concluded():
    """Test SessionDetailsTextDisplay with concluded session"""
    # Arrange
    mock_session = MagicMock(spec=Session)
    mock_session.type = Mock(value="session_value_data")
    mock_session.start_time = datetime(2025, 1, 1, 10, 0, 0)
    mock_session.end_time = datetime(2025, 1, 1, 12, 30, 0)
    mock_session.is_concluded = Mock(return_value=True)
    mock_session.get_checked_in_players = Mock(return_value=[Mock(), Mock(), Mock()])
    mock_session.get_official_start_time = Mock(return_value=datetime(2025, 1, 1, 10, 0, 0))
    mock_session.get_official_end_time = Mock(return_value=datetime(2025, 1, 1, 12, 30, 0))
    # Act
    display = SessionDetailsTextDisplay(session=mock_session)

    # Assert
    assert_that(display, is_(not_none()))
    assert_that(display.content, equal_to(
        f":video_game: **Type:** `session_value_data`\n\n"
        f":busts_in_silhouette: **Players:** 3 / 5\n\n"
        f":clock3: **Started:** <t:{int(datetime(2025, 1, 1, 10, 0, 0).timestamp())}:f>\n\n"
        f":stopwatch: **Ended:** <t:{int(datetime(2025, 1, 1, 12, 30, 0).timestamp())}:f>\n\n"
        f":hourglass: **Duration:** 2h 30m\n\n"
    ))


@pytest.mark.unit
def test_session_details_text_display_concluded_uses_official_session_window():
    """Test concluded duration excludes pre-session waiting time."""
    # Arrange
    mock_session = MagicMock(spec=Session)
    mock_session.type = Mock(value="session_value_data")
    mock_session.start_time = datetime(2025, 1, 1, 8, 0, 0)
    mock_session.end_time = datetime(2025, 1, 1, 12, 30, 0)
    mock_session.is_concluded = Mock(return_value=True)
    mock_session.get_checked_in_players = Mock(return_value=[Mock(), Mock(), Mock()])
    mock_session.get_official_start_time = Mock(return_value=datetime(2025, 1, 1, 10, 0, 0))
    mock_session.get_official_end_time = Mock(return_value=datetime(2025, 1, 1, 12, 30, 0))

    # Act
    display = SessionDetailsTextDisplay(session=mock_session)

    # Assert
    assert_that(display.content, equal_to(
        f":video_game: **Type:** `session_value_data`\n\n"
        f":busts_in_silhouette: **Players:** 3 / 5\n\n"
        f":clock3: **Started:** <t:{int(datetime(2025, 1, 1, 10, 0, 0).timestamp())}:f>\n\n"
        f":stopwatch: **Ended:** <t:{int(datetime(2025, 1, 1, 12, 30, 0).timestamp())}:f>\n\n"
        f":hourglass: **Duration:** 2h 30m\n\n"
    ))


@pytest.mark.unit
def test_edit_attendance_button_initialization():
    """Test EditAttendanceButton initializes correctly"""
    # Arrange
    mock_modal = Mock(spec=discord.ui.Modal)

    # Act
    button = EditAttendanceButton(modal=mock_modal)

    # Assert
    assert_that(button, is_(not_none()))
    assert_that(button.label, equal_to("Gestión asistencias"))
    assert_that(button.style, equal_to(discord.ButtonStyle.secondary))
    assert_that(button.custom_id, equal_to("edit_attendance_btn"))
    assert_that(button.modal, equal_to(mock_modal))


@pytest.mark.asyncio
@pytest.mark.unit
async def test_edit_attendance_button_callback():
    """Test EditAttendanceButton callback sends modal"""
    # Arrange
    mock_modal = Mock(spec=discord.ui.Modal)
    button = EditAttendanceButton(modal=mock_modal)
    mock_interaction = Mock(spec=discord.Interaction)
    mock_interaction.response.send_modal = AsyncMock()

    # Act
    await button.callback(mock_interaction)

    # Assert
    mock_interaction.response.send_modal.assert_called_once_with(mock_modal)


@pytest.mark.unit
def test_change_session_type_button_initialization():
    """Test ChangeSessionTypeButton initializes correctly"""
    # Arrange
    mock_modal = Mock(spec=discord.ui.Modal)

    # Act
    button = ChangeSessionTypeButton(modal=mock_modal)

    # Assert
    assert_that(button, is_(not_none()))
    assert_that(button.label, equal_to("Cambiar Tipo"))
    assert_that(button.style, equal_to(discord.ButtonStyle.secondary))
    assert_that(button.custom_id, equal_to("change_session_type_btn"))


@pytest.mark.asyncio
@pytest.mark.unit
async def test_change_session_type_button_callback():
    """Test ChangeSessionTypeButton callback sends modal"""
    # Arrange
    mock_modal = Mock(spec=discord.ui.Modal)
    button = ChangeSessionTypeButton(modal=mock_modal)
    mock_interaction = Mock(spec=discord.Interaction)
    mock_interaction.response.send_modal = AsyncMock()

    # Act
    await button.callback(mock_interaction)

    # Assert
    mock_interaction.response.send_modal.assert_called_once_with(mock_modal)


@pytest.mark.unit
def test_notify_missing_users_button_initialization():
    """Test NotifyMissingUsersButton initializes correctly"""
    # Arrange
    missing_users = ["123", "456"]

    # Act
    button = NotifyMissingUsersButton(missing_users=missing_users, cooldown_secs=30)

    # Assert
    assert_that(button, is_(not_none()))
    assert_that(button.label, equal_to("Notificar ausentes"))
    assert_that(button.missing_users, equal_to(missing_users))
    assert_that(button.cooldown_secs, equal_to(30))
    assert_that(button.last_usage, is_(None))


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notify_missing_users_button_callback_with_users():
    """Test NotifyMissingUsersButton callback with missing users"""
    # Arrange
    missing_users = ["123", "456"]
    button = NotifyMissingUsersButton(missing_users=missing_users)
    mock_interaction = Mock(spec=discord.Interaction)
    mock_interaction.response.send_message = AsyncMock()

    # Act
    await button.callback(mock_interaction)

    # Assert
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args[0][0]
    assert_that("<@123>" in call_args, is_(True))
    assert_that("<@456>" in call_args, is_(True))
    assert_that(button.last_usage, not_none())


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notify_missing_users_button_callback_no_users():
    """Test NotifyMissingUsersButton callback with no missing users"""
    # Arrange
    button = NotifyMissingUsersButton(missing_users=[])
    mock_interaction = Mock(spec=discord.Interaction)
    mock_interaction.response.send_message = AsyncMock()

    # Act
    await button.callback(mock_interaction)

    # Assert
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert_that("Ya se han conectado todos" in call_args[0][0], is_(True))


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notify_missing_users_button_cooldown():
    """Test NotifyMissingUsersButton cooldown functionality"""
    # Arrange
    missing_users = ["123"]
    button = NotifyMissingUsersButton(missing_users=missing_users, cooldown_secs=30)
    button.last_usage = datetime.now()
    mock_interaction = Mock(spec=discord.Interaction)
    mock_interaction.response.send_message = AsyncMock()

    # Act
    await button.callback(mock_interaction)

    # Assert
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert_that("Cooldown" in call_args[0][0], is_(True))


@pytest.mark.unit
def test_session_type_selector_initialization():
    """Test SessionTypeSelector initializes with all types"""
    # Arrange & Act
    selector = SessionTypeSelector(current_type=Type.OFFICIAL_GAME)

    # Assert
    assert_that(selector, is_(not_none()))
    assert_that(len(selector.options), equal_to(3))
    assert_that(selector.min_values, equal_to(1))
    assert_that(selector.max_values, equal_to(1))


@pytest.mark.unit
def test_session_type_selector_emoji_mapping():
    """Test SessionTypeSelector emoji mapping"""
    # Arrange
    selector = SessionTypeSelector(current_type=Type.OFFICIAL_GAME)

    # Act
    emoji_official = selector.get_emoji_for_type(Type.OFFICIAL_GAME)
    emoji_additional = selector.get_emoji_for_type(Type.ADDITIONAL_GAME)
    emoji_meeting = selector.get_emoji_for_type(Type.OFFICIAL_MEETING)

    # Assert
    assert_that(emoji_official, equal_to("📅"))
    assert_that(emoji_additional, equal_to("🎮"))
    assert_that(emoji_meeting, equal_to("🍻"))


@pytest.mark.unit
def test_session_type_selector_label_initialization():
    """Test SessionTypeSelectorLabel initializes correctly"""
    # Arrange & Act
    label = SessionTypeSelectorLabel(current_type=Type.OFFICIAL_GAME)

    # Assert
    assert_that(label, is_(not_none()))
    assert_that(label.text, equal_to("Tipo de sesión"))
    assert_that(label.component, instance_of(SessionTypeSelector))


@pytest.mark.unit
def test_user_selector_label_initialization():
    """Test UserSelectorLabel initializes correctly"""
    # Arrange
    user_ids = ["123", "456"]

    # Act
    label = UserSelectorLabel(
        text="Test Users",
        description="Test description",
        user_ids=user_ids
    )

    # Assert
    assert_that(label, is_(not_none()))
    assert_that(label.text, equal_to("Test Users"))
    assert_that(label.description, equal_to("Test description"))
    assert_that(label.component, instance_of(discord.ui.UserSelect))


@pytest.mark.unit
def test_motive_text_input_initialization():
    """Test MotiveTextInput initializes correctly"""
    # Arrange & Act
    text_input = MotiveTextInput(
        user_name="TestUser",
        user_id="123",
        motive="Test motive"
    )

    # Assert
    assert_that(text_input, is_(not_none()))
    assert_that(text_input.label, equal_to("TestUser: Motivo justificación"))
    assert_that(text_input.default, equal_to("Test motive"))
    assert_that(text_input.style, equal_to(discord.TextStyle.paragraph))
    assert_that(text_input.max_length, equal_to(200))
    assert_that(text_input.custom_id, equal_to("Motive-123"))
