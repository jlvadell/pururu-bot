from dataclasses import dataclass

from pururu.domain.messaging.events.base_events import SecondaryDomainEvent


# ---------------------------
# POLL EVENTS
# ---------------------------
@dataclass(frozen=True)
class CheckExpiredPollsEvent(SecondaryDomainEvent):
    event_type = "CheckExpiredPollsEvent"


@dataclass(frozen=True)
class FinalizePollEvent(SecondaryDomainEvent):
    event_type = "FinalizePollEvent"
    poll_id: str
