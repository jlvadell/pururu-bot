from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from hamcrest import assert_that, equal_to

from pururu.application.handlers.session_events_handler import SessionEventsHandler
from pururu.infrastructure.adapters.keronworld.session_packs_client import SessionPacksHttpResult
from pururu.domain.entities.session import Type, PlayerSession, SessionMetadataKey
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import (
    PlayerJoinedSessionEvent,
    PlayerLeftSessionEvent,
    SessionConcludeRequestedEvent,
    SessionConcludedEvent,
    SessionTypeChangeEvent,
    SessionAttendanceEditEvent,
    SessionAttendanceRepairEvent,
    SessionCreatedEvent,
    SessionUpdatedEvent,
    PlayerGameDetectedEvent,
    SessionGameEditEvent,
)
from pururu.domain.services.data_sync_service import DataSyncService
from pururu.domain.services.discord_service import DiscordService
from pururu.domain.services.session_service import SessionService


@pytest.fixture
def mock_session_service():
    """Create a mock SessionService for testing"""
    return MagicMock(spec=SessionService, name="SessionServiceMock")


@pytest.fixture
def mock_data_sync_service():
    """Create a mock DataSyncService for testing"""
    return MagicMock(spec=DataSyncService, name="DataSyncServiceMock")


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBus for testing"""
    return MagicMock(spec=EventBus, name="EventBusMock")


@pytest.fixture
def mock_discord_service():
    """Create a mock DiscordService for testing"""
    mock = AsyncMock(spec=DiscordService, name="DiscordServiceMock")
    mock.get_playing_game.return_value = None
    return mock


@pytest.fixture
def handler(mock_session_service, mock_data_sync_service, mock_event_bus, mock_discord_service):
    """Create a SessionEventsHandler instance with mocked dependencies"""
    return SessionEventsHandler(mock_session_service, mock_data_sync_service, mock_event_bus, mock_discord_service)


@pytest.mark.unit
def test_subscriptions(handler, mock_event_bus):
    """Test that the handler subscribes to the correct events"""
    # Arrange
    expected_calls = [
        ((PlayerJoinedSessionEvent.event_type, handler.handle_player_joined),),
        ((PlayerLeftSessionEvent.event_type, handler.handle_player_left),),
        ((SessionConcludeRequestedEvent.event_type, handler.handle_session_conclude_requested),),
        ((SessionConcludedEvent.event_type, handler.handle_session_concluded),),
        ((SessionTypeChangeEvent.event_type, handler.handle_session_type_change),),
        ((SessionAttendanceEditEvent.event_type, handler.handle_session_attendance_edit),),
        ((SessionAttendanceRepairEvent.event_type, handler.handle_session_attendance_repair),),
        ((SessionCreatedEvent.event_type, handler.handle_session_created),),
        ((SessionUpdatedEvent.event_type, handler.handle_session_updated),),
        ((PlayerGameDetectedEvent.event_type, handler.handle_player_game_detected),),
        ((SessionGameEditEvent.event_type, handler.handle_session_game_edit),),
    ]
    # Assert
    mock_event_bus.subscribe.assert_has_calls(expected_calls, any_order=True)
    assert_that(mock_event_bus.subscribe.call_count, equal_to(len(expected_calls)))


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_player_joined(mock_settings, handler, mock_session_service, mock_discord_service):
    """Test handle_player_joined"""
    # Arrange
    mock_settings.discord.enable_communication_channel = True
    event_time = datetime(2025, 10, 1, 12, 0, 0)
    event = PlayerJoinedSessionEvent(datetime.now(), "player123", event_time)
    session_id = "session123"
    channel_id = "channel123"
    message_id = "message123"
    mock_session = MagicMock(id=session_id)
    mock_session.metadata = {
        SessionMetadataKey.DISCORD_INFO_MESSAGE_CHANNEL_ID: channel_id,
        SessionMetadataKey.DISCORD_INFO_MESSAGE_ID: message_id
    }

    mock_session_service.register_player_connection.return_value = mock_session

    # Act
    await handler.handle_player_joined(event)

    # Assert
    mock_session_service.register_player_connection.assert_called_once_with("player123", event_time)
    mock_discord_service.get_playing_game.assert_awaited_once_with("player123")
    mock_session_service.record_player_game.assert_not_called()
    assert_update_session_info_view(mock_discord_service, channel_id, message_id, mock_session)


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_player_joined_records_playing_game(mock_settings, handler, mock_session_service,
                                                         mock_discord_service):
    mock_settings.discord.enable_communication_channel = False
    event_time = datetime(2025, 10, 1, 12, 0, 0)
    event = PlayerJoinedSessionEvent(datetime.now(), "player123", event_time)
    mock_session_service.register_player_connection.return_value = MagicMock(id="session123", metadata={})
    mock_discord_service.get_playing_game.return_value = "League of Legends"
    refreshed_session = MagicMock(id="session123", metadata={})
    mock_session_service.find_session_by_id.return_value = refreshed_session

    await handler.handle_player_joined(event)

    mock_session_service.record_player_game.assert_called_once_with("player123", "League of Legends")
    mock_session_service.find_session_by_id.assert_called_once_with("session123")


@pytest.mark.unit
def test_handle_player_left(handler, mock_session_service):
    """Test handle_player_left"""
    # Arrange
    event_time = datetime(2025, 10, 1, 12, 30, 0)
    event = PlayerLeftSessionEvent(datetime.now(), "player123", event_time)

    # Act
    handler.handle_player_left(event)

    # Assert
    mock_session_service.register_player_disconnection.assert_called_once_with("player123", event_time)


@pytest.mark.unit
def test_handle_session_conclude_requested(handler, mock_session_service):
    """Test handle_session_conclude_requested"""
    # Arrange
    end_time = datetime(2025, 10, 1, 15, 0, 0)
    event = SessionConcludeRequestedEvent(datetime.now(), "session123", end_time)

    # Act
    handler.handle_session_conclude_requested(event)

    # Assert
    mock_session_service.conclude_session.assert_called_once_with("session123", end_time)


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_session_concluded_with_positive_conclusion(mock_settings, handler, mock_session_service,
                                                                 mock_data_sync_service,
                                                                 mock_discord_service):
    """Test handle_session_concluded when the session was concluded positively"""
    # Arrange
    mock_settings.keronworld.enabled = False
    mock_settings.discord.enable_communication_channel = True
    session_id = "session123"
    channel_id = "channel123"
    message_id = "message123"
    mock_session = MagicMock(id=session_id)
    mock_session.metadata = {
        SessionMetadataKey.DISCORD_INFO_MESSAGE_CHANNEL_ID: channel_id,
        SessionMetadataKey.DISCORD_INFO_MESSAGE_ID: message_id
    }
    mock_session.was_concluded_positively.return_value = True
    mock_session_service.find_session_by_id.return_value = mock_session

    event = SessionConcludedEvent(datetime.now(), session_id)

    # Act
    await handler.handle_session_concluded(event)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with(session_id)
    assert_sync_session(mock_data_sync_service, mock_session)
    assert_update_session_info_view(mock_discord_service, channel_id, message_id, mock_session)


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_session_concluded_comms_disables(mock_settings, handler, mock_session_service,
                                                       mock_data_sync_service,
                                                       mock_discord_service):
    """Test handle_session_concluded do not update message when comms are disabled"""
    # Arrange
    mock_settings.keronworld.enabled = False
    mock_settings.discord.enable_communication_channel = False
    session_id = "session123"
    channel_id = "channel123"
    message_id = "message123"
    mock_session = MagicMock(id=session_id)
    mock_session.metadata = {
        SessionMetadataKey.DISCORD_INFO_MESSAGE_CHANNEL_ID: channel_id,
        SessionMetadataKey.DISCORD_INFO_MESSAGE_ID: message_id
    }
    mock_session.was_concluded_positively.return_value = True
    mock_session_service.find_session_by_id.return_value = mock_session

    event = SessionConcludedEvent(datetime.now(), session_id)

    # Act
    await handler.handle_session_concluded(event)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with(session_id)
    assert_sync_session(mock_data_sync_service, mock_session)
    mock_discord_service.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_session_concluded_with_negative_conclusion(mock_settings, handler, mock_session_service,
                                                                 mock_data_sync_service, mock_discord_service):
    """Test handle_session_concluded when the session was not concluded positively"""
    # Arrange
    mock_settings.discord.enable_communication_channel = True
    session_id = "session123"
    channel_id = "channel123"
    message_id = "message123"
    mock_session = MagicMock(id=session_id)
    mock_session.metadata = {
        SessionMetadataKey.DISCORD_INFO_MESSAGE_CHANNEL_ID: channel_id,
        SessionMetadataKey.DISCORD_INFO_MESSAGE_ID: message_id
    }
    mock_session.was_concluded_positively.return_value = False
    mock_session_service.find_session_by_id.return_value = mock_session

    event = SessionConcludedEvent(datetime.now(), "session123")

    # Act
    await handler.handle_session_concluded(event)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with("session123")
    assert mock_session.was_concluded_positively.call_count == 2
    mock_data_sync_service.sync_session.assert_not_called()
    assert_update_session_info_view(mock_discord_service, channel_id, message_id, mock_session)


@pytest.mark.unit
def test_handle_session_type_change(handler, mock_session_service):
    """Test handle_session_type_change"""
    # Arrange
    new_type = Type.OFFICIAL_GAME
    event = SessionTypeChangeEvent(datetime.now(), "session123", new_type.value)

    # Act
    handler.handle_session_type_change(event)

    # Assert
    mock_session_service.change_session_type.assert_called_once_with("session123", new_type)


@pytest.mark.unit
def test_handle_session_attendance_edit(handler, mock_session_service, mock_data_sync_service,
                                        mock_discord_service):
    """Test handle_session_attendance_edit"""
    # Arrange
    event = SessionAttendanceEditEvent(datetime.now(), "session123", {"player1": True, "player2": False},
                                       {"player1": "Motive 1", "player2": "Motive 2"})
    player_sessions = [PlayerSession("player1", True, True, "Motive 1", []),
                       PlayerSession("player2", True, False, "Motive 2", [])]
    # Act
    handler.handle_session_attendance_edit(event)

    # Assert
    mock_session_service.edit_session_attendance.assert_called_once_with("session123", player_sessions)


@pytest.mark.unit
def test_handle_session_attendance_repair(handler, mock_session_service):
    event = SessionAttendanceRepairEvent(datetime.now(), "session123", ["player1", "player2"])

    handler.handle_session_attendance_repair(event)

    mock_session_service.repair_session_attendance.assert_called_once_with(
        "session123", ["player1", "player2"])


@pytest.mark.unit
def test_handle_player_game_detected(handler, mock_session_service):
    event = PlayerGameDetectedEvent(datetime.now(), "player123", "VALORANT")

    handler.handle_player_game_detected(event)

    mock_session_service.record_player_game.assert_called_once_with("player123", "VALORANT")


@pytest.mark.unit
def test_handle_session_game_edit(handler, mock_session_service):
    event = SessionGameEditEvent(datetime.now(), "session123", "Minecraft")

    handler.handle_session_game_edit(event)

    mock_session_service.set_session_game.assert_called_once_with("session123", "Minecraft")


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_session_created_comms_disables(mock_settings, handler, mock_session_service,
                                                     mock_discord_service):
    """Test handle_session_created communication is disabled"""
    # Arrange
    mock_settings.discord.enable_communication_channel = False
    event = SessionCreatedEvent(datetime.now(), "1234", datetime.now())

    # Act
    await handler.handle_session_created(event)

    # Assert
    mock_session_service.assert_not_called()
    mock_discord_service.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_session_created(mock_settings, handler, mock_session_service, mock_discord_service):
    """Test handle_session_created"""
    # Arrange
    session_id = "session123"
    channel_id = "channel123"
    message_id = "message123"
    mock_session = MagicMock(id=session_id)
    mock_session_service.find_session_by_id.return_value = mock_session
    mock_settings.discord.discord_communication_channel_id = channel_id
    mock_settings.discord.enable_communication_channel = True
    mock_discord_service.send_session_info_view_message.return_value = message_id
    expected_metadata = {
        SessionMetadataKey.DISCORD_INFO_MESSAGE_CHANNEL_ID: channel_id,
        SessionMetadataKey.DISCORD_INFO_MESSAGE_ID: message_id
    }

    event = SessionCreatedEvent(datetime.now(), session_id, datetime.now())

    # Act
    await handler.handle_session_created(event)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with(session_id)
    mock_discord_service.send_session_info_view_message.assert_awaited_once_with(channel_id, mock_session)
    mock_session_service.add_session_metadata.assert_called_once_with(session_id, expected_metadata)


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_session_created_message_fail(mock_settings, handler, mock_session_service, mock_discord_service):
    """Test handle_session_created do not set metadata if message sending fails"""
    # Arrange
    session_id = "session123"
    channel_id = "channel123"
    message_id = None
    mock_session = MagicMock(id=session_id)
    mock_session_service.find_session_by_id.return_value = mock_session
    mock_settings.discord.discord_communication_channel_id = channel_id
    mock_discord_service.send_session_info_view_message.return_value = message_id

    event = SessionCreatedEvent(datetime.now(), session_id, datetime.now())

    # Act
    await handler.handle_session_created(event)

    # Assert
    mock_session_service.find_session_by_id.assert_called_once_with(session_id)
    mock_discord_service.send_session_info_view_message.assert_awaited_once_with(channel_id, mock_session)
    mock_session_service.add_session_metadata.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_session_updated(mock_settings, handler, mock_session_service, mock_data_sync_service,
                                      mock_discord_service):
    """Test handle_session_updated"""
    # Arrange
    mock_settings.discord.enable_communication_channel = True
    session_id = "session123"
    mock_session = MagicMock(id=session_id)
    channel_id = "channel123"
    message_id = "message123"
    mock_session.metadata = {
        SessionMetadataKey.DISCORD_INFO_MESSAGE_CHANNEL_ID: channel_id,
        SessionMetadataKey.DISCORD_INFO_MESSAGE_ID: message_id
    }

    mock_session_service.find_session_by_id.return_value = mock_session
    event = SessionUpdatedEvent(datetime.now(), session_id)

    # Act
    await handler.handle_session_updated(event)

    # Assert
    assert_update_session_info_view(mock_discord_service, channel_id, message_id, mock_session)
    assert_sync_session(mock_data_sync_service, mock_session)


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_session_updated_comms_disabled(mock_settings, handler, mock_session_service,
                                                     mock_data_sync_service, mock_discord_service):
    """Test handle_session_updated cooms disabled"""
    # Arrange
    mock_settings.discord.enable_communication_channel = False
    session_id = "session123"
    mock_session = MagicMock(id=session_id)
    channel_id = "channel123"
    message_id = "message123"
    mock_session.metadata = {
        SessionMetadataKey.DISCORD_INFO_MESSAGE_CHANNEL_ID: channel_id,
        SessionMetadataKey.DISCORD_INFO_MESSAGE_ID: message_id
    }

    mock_session_service.find_session_by_id.return_value = mock_session
    event = SessionUpdatedEvent(datetime.now(), session_id)

    # Act
    await handler.handle_session_updated(event)

    # Assert
    assert_sync_session(mock_data_sync_service, mock_session)
    mock_discord_service.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_session_updated_metadata_not_present(mock_settings, handler, mock_session_service,
                                                           mock_data_sync_service, mock_discord_service):
    """Test handle_session_updated metadata not present"""
    # Arrange
    mock_settings.discord.enable_communication_channel = True
    session_id = "session123"
    mock_session = MagicMock(id=session_id)
    mock_session.metadata = {}

    mock_session_service.find_session_by_id.return_value = mock_session
    event = SessionUpdatedEvent(datetime.now(), session_id)

    # Act
    await handler.handle_session_updated(event)

    # Assert
    assert_sync_session(mock_data_sync_service, mock_session)
    mock_discord_service.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch('pururu.application.handlers.session_events_handler.settings')
async def test_handle_session_updated_on_going_session(mock_settings, handler, mock_session_service,
                                                       mock_data_sync_service):
    """Test handle_session_updated ongoing/discarded session should not sync"""
    # Arrange
    mock_settings.discord.enable_communication_channel = False
    session_id = "session123"
    mock_session = MagicMock(id=session_id)
    mock_session.was_concluded_positively.return_value = False

    mock_session_service.find_session_by_id.return_value = mock_session
    event = SessionUpdatedEvent(datetime.now(), session_id)

    # Act
    await handler.handle_session_updated(event)

    # Assert
    mock_data_sync_service.assert_not_called()



def _player(player_id: str, attended: bool) -> MagicMock:
    player = MagicMock(spec=PlayerSession)
    player.player_id = player_id
    player.attended = attended
    return player


def _enable_keronworld(mock_settings, channel_id="channel123"):
    mock_settings.keronworld.enabled = True
    mock_settings.keronworld.packs_url = "https://api.keronworld.org/api/internal/session-packs"
    mock_settings.keronworld.packs_secret = "test-pack-webhook-secret"
    mock_settings.keronworld.app_url = "https://app.keronworld.org"
    mock_settings.discord.enable_communication_channel = True
    mock_settings.discord.discord_communication_channel_id = channel_id


@pytest.mark.unit
@pytest.mark.asyncio
@patch("pururu.application.handlers.session_events_handler.post_session_packs", new_callable=AsyncMock)
@patch("pururu.application.handlers.session_events_handler.settings")
async def test_handle_session_concluded_discarded_does_not_notify_keronworld(
        mock_settings, mock_post_session_packs, handler, mock_session_service, mock_data_sync_service,
        mock_discord_service):
    """Discarded sessions must not call KeroWorld even if pack notify is enabled."""
    _enable_keronworld(mock_settings)
    session_id = "session123"
    mock_session = MagicMock(id=session_id)
    mock_session.metadata = {}
    mock_session.was_concluded_positively.return_value = False
    mock_session.players = [_player("111", True)]
    mock_session_service.find_session_by_id.return_value = mock_session
    mock_settings.discord.enable_communication_channel = False

    await handler.handle_session_concluded(SessionConcludedEvent(datetime.now(), session_id))

    mock_post_session_packs.assert_not_called()
    mock_data_sync_service.sync_session.assert_not_called()
    mock_discord_service.send_simple_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch("pururu.application.handlers.session_events_handler.post_session_packs", new_callable=AsyncMock)
@patch("pururu.application.handlers.session_events_handler.settings")
async def test_handle_session_concluded_completed_notifies_keronworld(
        mock_settings, mock_post_session_packs, handler, mock_session_service, mock_data_sync_service,
        mock_discord_service):
    """Completed sessions with attendees should POST to KeroWorld and announce packs."""
    channel_id = "channel123"
    _enable_keronworld(mock_settings, channel_id)
    session_id = "session123"
    mock_session = MagicMock(id=session_id)
    mock_session.metadata = {}
    mock_session.was_concluded_positively.return_value = True
    mock_session.players = [_player("111", True), _player("222", False), _player("333", True)]
    mock_session.type = Type.OFFICIAL_GAME
    mock_session.get_game_name.return_value = "League of Legends"
    mock_session_service.find_session_by_id.return_value = mock_session
    mock_settings.discord.enable_communication_channel = False
    mock_post_session_packs.return_value = SessionPacksHttpResult(
        status_code=200,
        body={"success": True, "granted": ["111", "333"], "skipped": [], "missingChestType": False},
    )

    await handler.handle_session_concluded(SessionConcludedEvent(datetime.now(), session_id))

    mock_post_session_packs.assert_awaited_once_with(
        "https://api.keronworld.org/api/internal/session-packs",
        "test-pack-webhook-secret",
        {
            "sessionId": session_id,
            "attendees": [{"discordId": "111"}, {"discordId": "333"}],
            "sessionType": "Official Game",
            "gameName": "League of Legends",
        },
    )
    mock_discord_service.send_simple_message.assert_awaited_once_with(
        channel_id,
        "Hay un sobre de cartas para <@111> <@333>. Ábrelo en https://app.keronworld.org",
    )
    assert_sync_session(mock_data_sync_service, mock_session)


@pytest.mark.unit
@pytest.mark.asyncio
@patch("pururu.application.handlers.session_events_handler.post_session_packs", new_callable=AsyncMock)
@patch("pururu.application.handlers.session_events_handler.settings")
async def test_handle_session_concluded_completed_without_attendees_skips_notify(
        mock_settings, mock_post_session_packs, handler, mock_session_service, mock_discord_service):
    _enable_keronworld(mock_settings)
    mock_session = MagicMock(id="session123")
    mock_session.metadata = {}
    mock_session.was_concluded_positively.return_value = True
    mock_session.players = [_player("111", False)]
    mock_session_service.find_session_by_id.return_value = mock_session
    mock_settings.discord.enable_communication_channel = False

    await handler.handle_session_concluded(SessionConcludedEvent(datetime.now(), "session123"))

    mock_post_session_packs.assert_not_called()
    mock_discord_service.send_simple_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch("pururu.application.handlers.session_events_handler.post_session_packs", new_callable=AsyncMock)
@patch("pururu.application.handlers.session_events_handler.settings")
async def test_handle_session_concluded_keronworld_failure_does_not_raise_or_announce(
        mock_settings, mock_post_session_packs, handler, mock_session_service, mock_data_sync_service,
        mock_discord_service):
    _enable_keronworld(mock_settings)
    mock_session = MagicMock(id="session123")
    mock_session.metadata = {}
    mock_session.was_concluded_positively.return_value = True
    mock_session.players = [_player("111", True)]
    mock_session.type = Type.OFFICIAL_GAME
    mock_session.get_game_name.return_value = None
    mock_session_service.find_session_by_id.return_value = mock_session
    mock_settings.discord.enable_communication_channel = False
    mock_post_session_packs.return_value = None

    await handler.handle_session_concluded(SessionConcludedEvent(datetime.now(), "session123"))

    mock_post_session_packs.assert_awaited_once()
    mock_discord_service.send_simple_message.assert_not_called()
    assert_sync_session(mock_data_sync_service, mock_session)


@pytest.mark.unit
@pytest.mark.asyncio
@patch("pururu.application.handlers.session_events_handler.post_session_packs", new_callable=AsyncMock)
@patch("pururu.application.handlers.session_events_handler.settings")
async def test_handle_session_concluded_already_granted_sends_shorter_discord_message(
        mock_settings, mock_post_session_packs, handler, mock_session_service, mock_discord_service):
    _enable_keronworld(mock_settings)
    mock_session = MagicMock(id="session123")
    mock_session.metadata = {}
    mock_session.was_concluded_positively.return_value = True
    mock_session.players = [_player("111", True)]
    mock_session.type = Type.ADDITIONAL_GAME
    mock_session.get_game_name.return_value = None
    mock_session_service.find_session_by_id.return_value = mock_session
    mock_settings.discord.enable_communication_channel = False
    mock_post_session_packs.return_value = SessionPacksHttpResult(
        status_code=200,
        body={"success": True, "granted": [], "skipped": ["111"], "missingChestType": False},
    )

    await handler.handle_session_concluded(SessionConcludedEvent(datetime.now(), "session123"))

    mock_discord_service.send_simple_message.assert_awaited_once_with(
        "channel123",
        "Ya teníais sobre de esta sesión. https://app.keronworld.org",
    )



@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "enabled,packs_url,packs_secret",
    [
        (False, "https://api.keronworld.org/api/internal/session-packs", "test-pack-webhook-secret"),
        (True, "", "test-pack-webhook-secret"),
        (True, "https://api.keronworld.org/api/internal/session-packs", ""),
    ],
)
@patch("pururu.application.handlers.session_events_handler.post_session_packs", new_callable=AsyncMock)
@patch("pururu.application.handlers.session_events_handler.settings")
async def test_handle_session_concluded_skips_when_disabled_or_missing_config(
        mock_settings, mock_post_session_packs, enabled, packs_url, packs_secret,
        handler, mock_session_service, mock_discord_service):
    mock_settings.keronworld.enabled = enabled
    mock_settings.keronworld.packs_url = packs_url
    mock_settings.keronworld.packs_secret = packs_secret
    mock_settings.keronworld.app_url = "https://app.keronworld.org"
    mock_settings.discord.enable_communication_channel = False
    mock_session = MagicMock(id="session123")
    mock_session.metadata = {}
    mock_session.was_concluded_positively.return_value = True
    mock_session.players = [_player("111", True)]
    mock_session_service.find_session_by_id.return_value = mock_session

    await handler.handle_session_concluded(SessionConcludedEvent(datetime.now(), "session123"))

    mock_post_session_packs.assert_not_called()
    mock_discord_service.send_simple_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"success": True, "granted": ["111"], "skipped": [], "missingChestType": True},
        {"success": False, "granted": ["111"], "skipped": [], "missingChestType": False},
    ],
)
@patch("pururu.application.handlers.session_events_handler.post_session_packs", new_callable=AsyncMock)
@patch("pururu.application.handlers.session_events_handler.settings")
async def test_handle_session_concluded_does_not_send_discord_when_packs_not_granted(
        mock_settings, mock_post_session_packs, body, handler, mock_session_service, mock_discord_service):
    _enable_keronworld(mock_settings)
    mock_session = MagicMock(id="session123")
    mock_session.metadata = {}
    mock_session.was_concluded_positively.return_value = True
    mock_session.players = [_player("111", True)]
    mock_session.type = Type.OFFICIAL_GAME
    mock_session.get_game_name.return_value = None
    mock_session_service.find_session_by_id.return_value = mock_session
    mock_settings.discord.enable_communication_channel = False
    mock_post_session_packs.return_value = SessionPacksHttpResult(status_code=200, body=body)

    await handler.handle_session_concluded(SessionConcludedEvent(datetime.now(), "session123"))

    mock_post_session_packs.assert_awaited_once()
    mock_discord_service.send_simple_message.assert_not_called()


# ==================================================================
# Assertion Helpers
# ==================================================================

def assert_sync_session(mock_data_sync_service, mock_session):
    """Helper to assert that sync_session was called with the given session"""
    mock_data_sync_service.sync_session.assert_called_once_with(mock_session)


def assert_update_session_info_view(mock_discord_service, channel_id, message_id, session):
    """Helper to assert that update_session_info_view_message was not called"""
    mock_discord_service.update_session_info_view_message.assert_awaited_once_with(channel_id, message_id, session)
