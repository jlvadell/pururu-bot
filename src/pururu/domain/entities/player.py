from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Player:
    id: str
    name: str
    birthday: date
