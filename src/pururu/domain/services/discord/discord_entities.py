from dataclasses import dataclass


@dataclass
class SimpleMessage:
    channel_id: str
    content: str
    message_id: str | None = None
