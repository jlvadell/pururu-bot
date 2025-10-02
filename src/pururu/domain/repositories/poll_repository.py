from abc import ABC
from pururu.domain.entities.poll import PollReference

class PollRepository(ABC):
    def save(self, poll: PollReference) -> PollReference:
        pass

    def delete(self, poll_id: str) -> bool:
        pass

    def find_by_id(self, poll_id: str) -> PollReference | None:
        pass

    def find_all_expired(self) -> list[PollReference]:
        pass
