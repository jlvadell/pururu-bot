import dataclasses
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


@dataclass(frozen=True)
class DomainEvent:
    """Base class for domain events."""
    priority = ""
    event_type: str = dataclasses.field(init=False, default=None)
    created_at: datetime

    def __post_init__(self):
        object.__setattr__(self, 'event_type', self.__class__.__name__)

    def serialize(self) -> dict:
        """
        Converts the event instance into a JSON-serializable dictionary.
        Handles datetime and Enum fields.
        """
        def convert(value):
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [convert(v) for v in value]
            elif isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, Enum):
                return value.value
            else:
                return value

        serialized = {k: convert(v) for k, v in self.__dict__.items()}
        return serialized

    def idempotency_key(self) -> str:
        """Generate an idempotency key based on event data."""
        data = json.dumps(self.serialize(), sort_keys=True)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @classmethod
    def deserialize(cls, data: dict):
        """
        Converts a JSON-serializable dictionary back into a domain event instance.
        Handles datetime and Enum fields.
        """

        def convert_field(field_type, value):
            if value is None:
                return None
            elif field_type == datetime:
                return datetime.fromisoformat(value)
            elif hasattr(field_type, '__origin__') and field_type.__origin__ is list:
                # Handle list types
                inner_type = field_type.__args__[0] if field_type.__args__ else None
                return [convert_field(inner_type, item) for item in value]
            elif isinstance(field_type, type) and issubclass(field_type, Enum):
                return field_type(value)
            else:
                return value

        # Get field types for this dataclass
        field_types = {f.name: f.type for f in dataclasses.fields(cls)}

        # Convert values according to their field types
        converted_data = {}
        for key, value in data.items():
            if key in ["event_type"]:
                continue
            if key in field_types:
                converted_data[key] = convert_field(field_types[key], value)
            else:
                converted_data[key] = value  # Keep unknown fields as-is
        return cls(**converted_data)

    def get_age(self):
        """Returns the age of the event in seconds."""
        return (datetime.now() - self.created_at).total_seconds()


@dataclass(frozen=True)
class PrimaryDomainEvent(DomainEvent):
    """Base class for primary domain events."""
    priority = "Primary"


@dataclass(frozen=True)
class SecondaryDomainEvent(DomainEvent):
    """Base class for secondary domain events."""
    priority = "Secondary"
