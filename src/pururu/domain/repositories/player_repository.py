from abc import abstractmethod, ABC

from pururu.domain.entities.player import Player


class PlayerRepository(ABC):

    @abstractmethod
    def get_all(self) -> list[Player]:
        """
        Gets all players
        :return: list of players
        """
        pass
