import time

from sqlalchemy.orm import Session

from pururu.common import logger, metrics
from pururu.domain.entities.player import Player
from pururu.domain.repositories.player_repository import PlayerRepository
from pururu.infrastructure.adapters.postgres.engine import PostgresDBEngine
from pururu.infrastructure.adapters.postgres.entities import PlayerRecord
from pururu.infrastructure.adapters.postgres.mapper import PostgresMapper


class PostgresPlayerRepositoryImpl(PlayerRepository):

    def __init__(self, postgres_engine: PostgresDBEngine):
        self.postgres_engine = postgres_engine.get_engine()
        self.logger = logger.get_logger(__name__)

    def get_all(self) -> list[Player]:
        with Session(self.postgres_engine) as session:
            start = time.time()
            players = session.query(PlayerRecord).all()
            process_duration = time.time() - start
            metrics.database_operation_duration_seconds.labels(
                operation="get_all", table="player"
            ).observe(process_duration)
        return [PostgresMapper.map_record_to_player(player) for player in players]
