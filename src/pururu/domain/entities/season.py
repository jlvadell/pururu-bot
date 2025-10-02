from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Season:
    id: str
    president_id: str
    start_date: datetime
    end_date: datetime | None
