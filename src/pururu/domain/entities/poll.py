from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PollResolutionType(Enum):
    SEND_MESSAGE = "SEND_MESSAGE"

    def __str__(self):
        return self.value

    def __json__(self):
        return self.value


@dataclass
class PollReference:
    id: str
    channel_id: str
    expires_at: datetime | None
    resolution_type: PollResolutionType

@dataclass
class Poll(PollReference):
    question: str
    answers: list[str]
    duration_hours: int = 24
    allow_multiple: bool = False
    results: dict[str, int] = field(default_factory=dict)

    def get_winners(self) -> str:
        """
        Returns the answer with the most votes, or multiple answers if there is a tie.
        Multiple answers are returned as a comma-separated string.
        :return: answer with the most votes; string
        """
        max_votes = max(self.results.values())
        winners = [answer for answer, votes in self.results.items() if votes == max_votes]
        return ', '.join(winners)