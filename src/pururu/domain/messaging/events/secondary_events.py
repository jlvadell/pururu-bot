from dataclasses import dataclass

from pururu.domain.messaging.events.base_events import SecondaryDomainEvent


# ---------------------------
# POLL EVENTS
# ---------------------------
@dataclass(frozen=True)
class CheckExpiredPollsEvent(SecondaryDomainEvent):
    pass


@dataclass(frozen=True)
class FinalizePollEvent(SecondaryDomainEvent):
    poll_id: str
