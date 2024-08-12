from abc import ABC, abstractmethod

from domain.entities import Attendance, BotEvent, Clocking


class DatabaseInterface(ABC):
    @abstractmethod
    def upsert_attendance(self, attendance: Attendance):
        pass

    @abstractmethod
    def insert_clocking(self, clocking: Clocking):
        pass

    @abstractmethod
    def register_bot_event(self, bot_event: BotEvent):
        pass

    @abstractmethod
    def get_last_attendance(self):
        pass
