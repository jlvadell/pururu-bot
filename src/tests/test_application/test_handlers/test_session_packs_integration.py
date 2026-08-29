import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from hamcrest import assert_that, equal_to

from pururu.application.handlers.session_events_handler import SessionEventsHandler
from pururu.domain.entities.session import PlayerSession, Session, SessionMetadataKey, Status, Type
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import SessionConcludedEvent
from pururu.domain.services.data_sync_service import DataSyncService
from pururu.domain.services.discord_service import DiscordService
from pururu.domain.services.session_service import SessionService

PACKS_URL = "https://api.keronworld.org/api/internal/session-packs"
PACKS_SECRET = "test-pack-webhook-secret"
_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _enable_keronworld(mock_settings, channel_id="channel123"):
    mock_settings.keronworld.enabled = True
    mock_settings.keronworld.packs_url = PACKS_URL
    mock_settings.keronworld.packs_secret = PACKS_SECRET
    mock_settings.keronworld.app_url = "https://app.keronworld.org"
    mock_settings.discord.enable_communication_channel = False
    mock_settings.discord.discord_communication_channel_id = channel_id


def _patch_async_client(transport: httpx.MockTransport):
    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return _REAL_ASYNC_CLIENT(*args, **kwargs)

    return patch(
        "pururu.infrastructure.adapters.keronworld.session_packs_client.httpx.AsyncClient",
        side_effect=factory,
    )


def _completed_session() -> Session:
    return Session(
        id="session123",
        season_id="season456",
        type=Type.OFFICIAL_GAME,
        status=Status.COMPLETED,
        players=[
            PlayerSession("111", True, False, None, []),
            PlayerSession("222", False, False, None, []),
            PlayerSession("333", True, False, None, []),
        ],
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=datetime(2025, 10, 1, 12, 0, 0),
        metadata={SessionMetadataKey.GAME_NAME: "League of Legends"},
    )


@pytest.mark.integration
@pytest.mark.asyncio
@patch("pururu.application.handlers.session_events_handler.settings")
async def test_handler_posts_session_packs_through_httpx_when_enabled(mock_settings):
    _enable_keronworld(mock_settings)
    captured = {}

    def http_handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "granted": ["111", "333"], "skipped": [], "missingChestType": False},
        )

    session = _completed_session()
    session_service = MagicMock(spec=SessionService)
    session_service.find_session_by_id.return_value = session
    discord_service = AsyncMock(spec=DiscordService)
    handler = SessionEventsHandler(
        session_service,
        MagicMock(spec=DataSyncService),
        MagicMock(spec=EventBus),
        discord_service,
    )

    with _patch_async_client(httpx.MockTransport(http_handler)):
        await handler.handle_session_concluded(SessionConcludedEvent(datetime.now(), session.id))

    assert_that(captured["url"], equal_to(PACKS_URL))
    assert_that(captured["authorization"], equal_to(f"Bearer {PACKS_SECRET}"))
    assert_that(captured["payload"], equal_to({
        "sessionId": "session123",
        "attendees": [{"discordId": "111"}, {"discordId": "333"}],
        "sessionType": "Official Game",
        "gameName": "League of Legends",
    }))
    discord_service.send_simple_message.assert_awaited_once_with(
        "channel123",
        "Hay un sobre de cartas para <@111> <@333>. \u00c1brelo en https://app.keronworld.org",
    )
