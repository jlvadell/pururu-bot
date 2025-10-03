import dataclasses
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from pururu.common.utils import serialize, deserialize


@dataclass(frozen=True)
class DomainEvent:
    """Base class for domain events."""
    priority = ""
    event_type: str = dataclasses.field(init=False)
    created_at: datetime

    def serialize(self) -> dict:
        """
        Converts the event instance into a JSON-serializable dictionary.
        Handles datetime and Enum fields.
        """

        serialized = {k: serialize(v) for k, v in self.__dict__.items()}
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

        # Get field types for this dataclass
        field_types = {f.name: f.type for f in dataclasses.fields(cls)}

        # Convert values according to their field types
        converted_data = {}
        for key, value in data.items():
            if key in ["event_type"]:
                continue
            if key in field_types:
                converted_data[key] = deserialize(field_types[key], value)
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
