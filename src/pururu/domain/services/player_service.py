from pururu.domain.entities.player import Player
from pururu.domain.repositories.player_repository import PlayerRepository


class PlayerService:
    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def get_players(self) -> list[Player]:
        return self.player_repository.get_all()
