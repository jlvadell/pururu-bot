import time

from sqlalchemy import func
from sqlalchemy.orm import Session

from pururu.common import logger, metrics
from pururu.domain.entities.poll import PollReference
from pururu.domain.repositories.poll_repository import PollRepository
from pururu.infrastructure.adapters.postgres.engine import PostgresDBEngine
from pururu.infrastructure.adapters.postgres.entities import PollRecord
from pururu.infrastructure.adapters.postgres.mapper import PostgresMapper


class PostgresPollRepositoryImpl(PollRepository):

    def __init__(self, postgres_engine: PostgresDBEngine):
        self.postgres_engine = postgres_engine.get_engine()
        self.logger = logger.get_logger(__name__)

    def save(self, poll: PollReference) -> PollReference:
        with Session(self.postgres_engine) as session:
            start = time.time()
            record = PostgresMapper.map_poll_to_record(poll)
            session.add(record)
            session.commit()
            session.refresh(record)
            process_duration = time.time() - start
            metrics.database_operation_duration_seconds.labels(
                operation="save", table="poll"
            ).observe(process_duration)
            return PostgresMapper.map_record_to_poll(record)

    def delete(self, poll_id: str) -> bool:
        with Session(self.postgres_engine) as session:
            start = time.time()
            record = session.query(PollRecord).filter(PollRecord.id == poll_id).one_or_none()
            if not record:
                self.logger.warning(f"Poll record {poll_id} not found; cannot delete", extra={"poll_id": poll_id})
                return False
            session.delete(record)
            session.commit()
            process_duration = time.time() - start
            metrics.database_operation_duration_seconds.labels(
                operation="delete", table="poll"
            ).observe(process_duration)
            return True

    def find_by_id(self, poll_id: str) -> PollReference | None:
        with Session(self.postgres_engine) as session:
            start = time.time()
            record = session.query(PollRecord).filter(PollRecord.id == poll_id).one_or_none()
            if not record:
                return None
            process_duration = time.time() - start
            metrics.database_operation_duration_seconds.labels(
                operation="find_by_id", table="poll"
            ).observe(process_duration)
            return PostgresMapper.map_record_to_poll(record)

    def find_all_expired(self) -> list[PollReference]:
        with Session(self.postgres_engine) as session:
            start = time.time()
            records = session.query(PollRecord).filter(PollRecord.expires_at <= func.now()).all()
            process_duration = time.time() - start
            metrics.database_operation_duration_seconds.labels(
                operation="find_all_expired", table="poll"
            ).observe(process_duration)
            return [PostgresMapper.map_record_to_poll(record) for record in records]
