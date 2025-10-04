from abc import ABC, abstractmethod


class IdGeneratorService(ABC):
    @abstractmethod
    def next_id(self) -> str:
        pass
