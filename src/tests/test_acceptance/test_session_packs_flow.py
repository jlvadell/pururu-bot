import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from hamcrest import assert_that, equal_to, is_

from pururu.application.handlers.session_events_handler import SessionEventsHandler
from pururu.domain.entities.session import (
    GameSource,
    Interval,
    PlayerSession,
    Session,
    SessionMetadataKey,
    Status,
    Type,
)
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.messaging.events.session_events import SessionConcludedEvent
from pururu.domain.repositories.session_repository import SessionRepository
from pururu.domain.services.data_sync_service import DataSyncService
from pururu.domain.services.discord_service import DiscordService
from pururu.domain.services.id_generator_service import IdGeneratorService
from pururu.domain.services.player_service import PlayerService
from pururu.domain.services.season_service import SeasonService
from pururu.domain.services.session_service import SessionService

PACKS_URL = "https://api.keronworld.org/api/internal/session-packs"
PACKS_SECRET = "test-pack-webhook-secret"
_REAL_ASYNC_CLIENT = httpx.AsyncClient
START = datetime(2025, 10, 1, 10, 0, 0)


class InMemorySessionRepository(SessionRepository):
    def __init__(self, session: Session | None = None):
        self.session = session

    def save(self, session: Session) -> Session:
        self.session = session
        return session

    def update(self, session: Session) -> Session:
        self.session = session
        return session

    def find_by_id(self, session_id: str) -> Session | None:
        if self.session and self.session.id == session_id:
            return self.session
        return None

    def find_active_session(self) -> Session | None:
        if self.session and self.session.status == Status.DRAFT and self.session.end_time is None:
            return self.session
        return None

    def find_latest_by_type_and_status(self, session_type: Type, session_status: Status) -> Session | None:
        return None

    def find_completed_by_player_id(self, player_id: str, exclude_session_id: str | None = None) -> list[Session]:
        return []


def _player(player_id: str, seconds: int) -> PlayerSession:
    end = START + timedelta(seconds=seconds)
    return PlayerSession(
        player_id=player_id,
        attended=False,
        justified_absence=False,
        motive=None,
        intervals=[Interval(start=START, end=end)],
    )


def _draft_session(players: list[PlayerSession], game_name: str | None = None) -> Session:
    metadata = {}
    if game_name:
        metadata[SessionMetadataKey.GAME_NAME] = game_name
        metadata[SessionMetadataKey.GAME_SOURCE] = GameSource.AUTO.value
    return Session(
        id="session123",
        season_id="season456",
        type=Type.OFFICIAL_GAME,
        status=Status.DRAFT,
        players=players,
        start_time=START,
        end_time=None,
        metadata=metadata,
    )


def _build_service(session: Session) -> tuple[SessionService, InMemorySessionRepository, MagicMock]:
    repository = InMemorySessionRepository(session)
    event_bus = MagicMock(spec=EventBus)
    service = SessionService(
        repository,
        MagicMock(spec=SeasonService),
        MagicMock(spec=PlayerService),
        MagicMock(spec=IdGeneratorService),
        event_bus,
    )
    return service, repository, event_bus


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


def _published_concluded_event(event_bus) -> SessionConcludedEvent:
    events = [call.args[0] for call in event_bus.publish.call_args_list]
    concluded = [event for event in events if isinstance(event, SessionConcludedEvent)]
    assert_that(len(concluded), equal_to(1))
    return concluded[0]


@pytest.mark.integration
@pytest.mark.asyncio
@patch("pururu.application.handlers.session_events_handler.settings")
async def test_acceptance_completed_session_notifies_keronworld_with_game_name(mock_settings):
    _enable_keronworld(mock_settings)
    session = _draft_session(
        [_player("111", 60), _player("222", 60), _player("333", 0)],
        game_name="League of Legends",
    )
    service, repository, event_bus = _build_service(session)
    captured = {}

    def http_handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "granted": ["111", "222"], "skipped": [], "missingChestType": False},
        )

    discord_service = AsyncMock(spec=DiscordService)
    handler = SessionEventsHandler(
        service,
        MagicMock(spec=DataSyncService),
        event_bus,
        discord_service,
    )

    end_time = START + timedelta(seconds=60)
    service.conclude_session(session.id, end_time)
    stored = repository.find_by_id(session.id)
    assert_that(stored.was_concluded_positively(), is_(True))
    assert_that(stored.get_game_name(), equal_to("League of Legends"))

    with _patch_async_client(httpx.MockTransport(http_handler)):
        await handler.handle_session_concluded(_published_concluded_event(event_bus))

    assert_that(captured["url"], equal_to(PACKS_URL))
    assert_that(captured["authorization"], equal_to(f"Bearer {PACKS_SECRET}"))
    assert_that(captured["payload"], equal_to({
        "sessionId": "session123",
        "attendees": [{"discordId": "111"}, {"discordId": "222"}],
        "sessionType": "Official Game",
        "gameName": "League of Legends",
    }))
    discord_service.send_simple_message.assert_awaited_once()


@pytest.mark.integration
@pytest.mark.asyncio
@patch("pururu.application.handlers.session_events_handler.settings")
async def test_acceptance_discarded_session_does_not_notify_keronworld(mock_settings):
    _enable_keronworld(mock_settings)
    session = _draft_session([_player("111", 5)], game_name="League of Legends")
    service, repository, event_bus = _build_service(session)
    captured = {}

    def http_handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"success": True, "granted": ["111"], "skipped": [], "missingChestType": False})

    discord_service = AsyncMock(spec=DiscordService)
    handler = SessionEventsHandler(
        service,
        MagicMock(spec=DataSyncService),
        event_bus,
        discord_service,
    )

    end_time = START + timedelta(seconds=5)
    service.conclude_session(session.id, end_time)
    stored = repository.find_by_id(session.id)
    assert_that(stored.status, equal_to(Status.DISCARDED))
    assert_that(stored.was_concluded_positively(), is_(False))

    with _patch_async_client(httpx.MockTransport(http_handler)):
        await handler.handle_session_concluded(_published_concluded_event(event_bus))

    assert_that(captured, equal_to({}))
    discord_service.send_simple_message.assert_not_called()
