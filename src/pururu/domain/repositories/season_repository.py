from abc import ABC, abstractmethod

from pururu.domain.entities.season import Season


class SeasonRepository(ABC):

    @abstractmethod
    def get_current_season(self) -> Season | None:
        """
        Gets the current season
        :return: the current season
        """
        pass
