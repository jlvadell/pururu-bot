from abc import ABC, abstractmethod

from domain.entities import BotEvent


class PururuInterface(ABC):
    @abstractmethod
    def register_bot_event(self, event: BotEvent):
        pass

    @abstractmethod
    def register_new_player(self, player: str):
        pass

    @abstractmethod
    def remove_player(self, player: str):
        pass

    @abstractmethod
    def register_new_game(self):
        pass

    @abstractmethod
    def end_game(self):
        pass
