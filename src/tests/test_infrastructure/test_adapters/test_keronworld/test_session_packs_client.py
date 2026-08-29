from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from hamcrest import assert_that, equal_to, has_entries, is_, none, not_none

from pururu.infrastructure.adapters.keronworld.session_packs_client import post_session_packs

PACKS_URL = "https://api.keronworld.org/api/internal/session-packs"
PACKS_SECRET = "test-pack-webhook-secret"


def _mock_async_client(post_side_effect=None, post_return_value=None):
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=post_side_effect, return_value=post_return_value)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    return mock_client


def _json_response(status_code: int, body: dict, is_success: bool | None = None):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.is_success = (200 <= status_code < 300) if is_success is None else is_success
    mock_response.json.return_value = body
    return mock_response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_session_packs_sends_bearer_payload_and_parses_granted():
    mock_response = _json_response(200, {
        "success": True,
        "granted": ["111"],
        "skipped": [],
        "missingChestType": False,
    })
    mock_client = _mock_async_client(post_return_value=mock_response)
    payload = {"sessionId": "session123", "attendees": [{"discordId": "111"}]}

    with patch(
            "pururu.infrastructure.adapters.keronworld.session_packs_client.httpx.AsyncClient",
            return_value=mock_client,
    ) as mock_async_client_cls:
        result = await post_session_packs(PACKS_URL, PACKS_SECRET, payload)

    mock_async_client_cls.assert_called_once_with(timeout=10.0)
    mock_client.post.assert_awaited_once()
    args, kwargs = mock_client.post.await_args
    assert_that(args[0], equal_to(PACKS_URL))
    assert_that(kwargs["json"], equal_to(payload))
    assert_that(kwargs["headers"]["Authorization"], equal_to(f"Bearer {PACKS_SECRET}"))
    assert_that(result, not_none())
    assert_that(result.status_code, equal_to(200))
    assert_that(result.body["granted"], equal_to(["111"]))
    assert_that(result.body["skipped"], equal_to([]))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_session_packs_parses_skipped_on_2xx():
    mock_response = _json_response(200, {
        "success": True,
        "granted": [],
        "skipped": ["111", "333"],
        "missingChestType": False,
    })
    mock_client = _mock_async_client(post_return_value=mock_response)

    result = None
    with patch(
            "pururu.infrastructure.adapters.keronworld.session_packs_client.httpx.AsyncClient",
            return_value=mock_client,
    ):
        result = await post_session_packs(
            PACKS_URL, PACKS_SECRET, {"sessionId": "session123", "attendees": [{"discordId": "111"}]},
        )

    assert_that(result.status_code, equal_to(200))
    assert_that(result.body, has_entries(granted=[], skipped=["111", "333"], success=True))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_session_packs_swallows_http_errors():
    mock_client = _mock_async_client(post_side_effect=httpx.ConnectError("down"))

    with patch(
            "pururu.infrastructure.adapters.keronworld.session_packs_client.httpx.AsyncClient",
            return_value=mock_client,
    ):
        result = await post_session_packs(PACKS_URL, PACKS_SECRET, {"sessionId": "session123"})

    assert_that(result, is_(none()))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_session_packs_swallows_timeouts():
    mock_client = _mock_async_client(post_side_effect=httpx.TimeoutException("timed out"))

    with patch(
            "pururu.infrastructure.adapters.keronworld.session_packs_client.httpx.AsyncClient",
            return_value=mock_client,
    ):
        result = await post_session_packs(PACKS_URL, PACKS_SECRET, {"sessionId": "session123"})

    assert_that(result, is_(none()))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_session_packs_returns_5xx_without_raising():
    mock_response = _json_response(503, {"success": False, "error": "unavailable"})
    mock_client = _mock_async_client(post_return_value=mock_response)

    result = None
    with patch(
            "pururu.infrastructure.adapters.keronworld.session_packs_client.httpx.AsyncClient",
            return_value=mock_client,
    ):
        result = await post_session_packs(PACKS_URL, PACKS_SECRET, {"sessionId": "session123"})

    assert_that(result, not_none())
    assert_that(result.status_code, equal_to(503))
    assert_that(result.body["success"], equal_to(False))
