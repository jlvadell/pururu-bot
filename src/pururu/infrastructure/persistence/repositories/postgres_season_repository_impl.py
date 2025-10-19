import time

from sqlalchemy.orm import Session

from pururu.common import logger, metrics
from pururu.domain.entities.season import Season
from pururu.domain.repositories.season_repository import SeasonRepository
from pururu.infrastructure.adapters.postgres.engine import PostgresDBEngine
from pururu.infrastructure.adapters.postgres.entities import SeasonRecord
from pururu.infrastructure.adapters.postgres.mapper import PostgresMapper


class PostgresSeasonRepositoryImpl(SeasonRepository):

    def __init__(self, postgres_engine: PostgresDBEngine):
        self.postgres_engine = postgres_engine.get_engine()
        self.logger = logger.get_logger(__name__)

    def get_current_season(self) -> Season | None:
        with Session(self.postgres_engine) as session:
            start = time.time()
            season = session.query(SeasonRecord).filter(SeasonRecord.end_date.is_(None)).one_or_none()
            if not season:
                self.logger.warning('No season active found in the database.')
                return None
            process_duration = time.time() - start
            metrics.database_operation_duration_seconds.labels(
                operation="get_current_season", table="season"
            ).observe(process_duration)
            return PostgresMapper.map_record_to_season(season)
