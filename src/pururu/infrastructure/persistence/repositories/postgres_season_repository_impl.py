from sqlalchemy.orm import Session

from pururu.domain.entities.season import Season
from pururu.domain.repositories.season_repository import SeasonRepository
from pururu.infrastructure.adapters.postgres.engine import PostgresDBEngine
from pururu.infrastructure.adapters.postgres.entities import SeasonRecord
from pururu.infrastructure.adapters.postgres.mapper import PostgresMapper


class PostgresSeasonRepositoryImpl(SeasonRepository):

    def __init__(self, postgres_engine: PostgresDBEngine):
        self.postgres_engine = postgres_engine.get_engine()

    def get_current_season(self) -> Season | None:
        with Session(self.postgres_engine) as session:
            season = session.query(SeasonRecord).filter(SeasonRecord.end_date == None).one_or_none()
            if not season:
                return None
            return PostgresMapper.map_record_to_season(season)
