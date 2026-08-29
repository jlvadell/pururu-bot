from dataclasses import dataclass, field

import httpx

from pururu.common import logger

_DEFAULT_TIMEOUT_SECONDS = 10.0

_logger = logger.get_logger(__name__)


@dataclass(frozen=True)
class SessionPacksHttpResult:
    status_code: int
    body: dict = field(default_factory=dict)


async def post_session_packs(
        url: str,
        secret: str,
        payload: dict,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
) -> SessionPacksHttpResult | None:
    """
    Notify KeroWorld that a session concluded so attendees can receive card packs.

    Never raises: returns None on network/client errors so the session flow cannot fail
    because KeroWorld is down.
    """
    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    session_id = payload.get("sessionId")
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        _logger.error(
            "KeroWorld session-packs request failed",
            extra={"session_id": session_id, "url": url, "error": str(exc)},
            exc_info=True,
        )
        return None
    except Exception as exc:
        _logger.error(
            "Unexpected error notifying KeroWorld session-packs",
            extra={"session_id": session_id, "url": url, "error": str(exc)},
            exc_info=True,
        )
        return None

    body: dict = {}
    try:
        parsed = response.json()
        if isinstance(parsed, dict):
            body = parsed
    except ValueError:
        _logger.warning(
            "KeroWorld session-packs response was not JSON",
            extra={"session_id": session_id, "status_code": response.status_code},
        )

    if not response.is_success:
        _logger.error(
            "KeroWorld session-packs returned a non-success status",
            extra={
                "session_id": session_id,
                "status_code": response.status_code,
                "success": body.get("success"),
            },
        )
    else:
        _logger.info(
            "KeroWorld session-packs notified",
            extra={
                "session_id": session_id,
                "status_code": response.status_code,
                "granted_count": len(body.get("granted") or []),
                "skipped_count": len(body.get("skipped") or []),
                "missing_chest_type": body.get("missingChestType"),
            },
        )

    return SessionPacksHttpResult(status_code=response.status_code, body=body)
