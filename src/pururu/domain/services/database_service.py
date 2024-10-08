from abc import ABC, abstractmethod

from pururu.domain.entities import Attendance, BotEvent, Clocking


class DatabaseInterface(ABC):
    @abstractmethod
    def upsert_attendance(self, attendance: Attendance) -> None:
        pass

    @abstractmethod
    def get_all_attendances(self) -> list[Attendance]:
        pass

    @abstractmethod
    def upsert_clocking(self, clocking: Clocking) -> None:
        pass

    @abstractmethod
    def insert_bot_event(self, bot_event: BotEvent) -> None:
        pass

    @abstractmethod
    def get_last_attendance(self) -> Attendance:
        pass

    @abstractmethod
    def get_player_coins(self, player: str) -> int:
        pass
