from sqlalchemy.orm import Session

from pururu.domain.entities.player import Player
from pururu.domain.repositories.player_repository import PlayerRepository
from pururu.infrastructure.adapters.postgres.engine import PostgresDBEngine
from pururu.infrastructure.adapters.postgres.entities import PlayerRecord
from pururu.infrastructure.adapters.postgres.mapper import PostgresMapper


class PostgresPlayerRepositoryImpl(PlayerRepository):

    def __init__(self, postgres_engine: PostgresDBEngine):
        self.postgres_engine = postgres_engine.get_engine()

    def get_all(self) -> list[Player]:
        with Session(self.postgres_engine) as session:
            players = session.query(PlayerRecord).all()
        return [PostgresMapper.map_record_to_player(player) for player in players]
