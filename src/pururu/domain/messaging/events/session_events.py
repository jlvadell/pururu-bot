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


@dataclass(frozen=True)
class SessionTypeChangeEvent(PrimaryDomainEvent):
    """
    Event representing an intention to change the type of a session.
    """
    event_type = "SessionTypeChangeEvent"
    session_id: str
    new_type: str


@dataclass(frozen=True)
class SessionAttendanceEditEvent(PrimaryDomainEvent):
    """
    Event representing the intention to update the attendance data of session.
    """
    event_type = "SessionAttendanceEditEvent"
    session_id: str
    justified_absences: dict[str, bool]  # player_id -> justified_absence
    motives: dict[str, str]  # player_id -> motive


@dataclass(frozen=True)
class SessionAttendanceRepairEvent(PrimaryDomainEvent):
    """
    Event representing confirmed attendees whose Discord connection data was incomplete.
    """
    event_type = "SessionAttendanceRepairEvent"
    session_id: str
    player_ids: list[str]


@dataclass(frozen=True)
class SessionCreatedEvent(PrimaryDomainEvent):
    """
    Event representing a session creation.
    """
    event_type = "SessionCreatedEvent"
    session_id: str
    date: datetime


@dataclass(frozen=True)
class SessionUpdatedEvent(PrimaryDomainEvent):
    """
    Event representing a session being updated outside the main flow.
    """
    event_type = "SessionUpdatedEvent"
    session_id: str


@dataclass(frozen=True)
class PlayerGameDetectedEvent(PrimaryDomainEvent):
    """
    Event representing a tracked player seen playing a game while in a voice session.
    """
    event_type = "PlayerGameDetectedEvent"
    player_id: str
    game_name: str


@dataclass(frozen=True)
class SessionGameEditEvent(PrimaryDomainEvent):
    """
    Event representing a manual edit of the session game name.
    """
    event_type = "SessionGameEditEvent"
    session_id: str
    game_name: str
