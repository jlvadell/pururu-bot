from abc import abstractmethod, ABC

from pururu.domain.entities.session import Session


class DataSyncService(ABC):
    @abstractmethod
    def sync_session(self, session: Session) -> None:
        pass
