from dataclasses import dataclass
from datetime import datetime

from pururu.domain.messaging.events.base_events import PrimaryDomainEvent


@dataclass(frozen=True)
class PlayerJoinedSessionEvent(PrimaryDomainEvent):
    """
    Event representing a player joining a game session.
    """
    event_type = "PlayerJoinedSessionEvent"
    player_id: str
    time: datetime


@dataclass(frozen=True)
class PlayerLeftSessionEvent(PrimaryDomainEvent):
    """
    Event representing a player leaving a game session.
    """
    event_type = "PlayerLeftSessionEvent"
    player_id: str
    time: datetime


@dataclass(frozen=True)
class SessionConcludeRequestedEvent(PrimaryDomainEvent):
    """
    Event triggered when no players remain connected, indicating the session should be concluded.
    """
    event_type = "SessionConcludeRequestedEvent"
    session_id: str
    end_time: datetime


@dataclass(frozen=True)
class SessionConcludedEvent(PrimaryDomainEvent):
    """
    Event representing the successful conclusion of a game session.
    """
    event_type = "SessionConcludedEvent"
    session_id: str
