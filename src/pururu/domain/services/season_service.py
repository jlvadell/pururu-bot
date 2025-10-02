from pururu.domain.entities.season import Season
from pururu.domain.repositories.season_repository import SeasonRepository


class SeasonService:
    def __init__(self, season_repository: SeasonRepository):
        self.season_repository = season_repository

    def get_current_season(self) -> Season:
        """
        Gets the current active season
        :return: the current season if found, None otherwise
        """
        return self.season_repository.get_current_season()
