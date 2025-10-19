import time

from sqlalchemy import and_
from sqlalchemy.orm import Session as OrmSession

from pururu.common import logger, metrics
from pururu.domain.entities.session import Session, Status, Type
from pururu.domain.exceptions import OptimisticLockingFailureException
from pururu.domain.repositories.session_repository import SessionRepository
from pururu.infrastructure.adapters.postgres.engine import PostgresDBEngine
from pururu.infrastructure.adapters.postgres.entities import SessionRecord
from pururu.infrastructure.adapters.postgres.mapper import PostgresMapper


class PostgresSessionRepositoryImpl(SessionRepository):
    def __init__(self, postgres_engine: PostgresDBEngine):
        self.postgres_engine = postgres_engine.get_engine()
        self.logger = logger.get_logger(__name__)

    def save(self, session: Session) -> Session:
        record = PostgresMapper.map_session_to_record(session)
        with OrmSession(self.postgres_engine) as orm_session:
            self.logger.debug(f"Saving new session with id {session.id} and version {session.version}")
            start = time.time()
            orm_session.add(record)
            orm_session.commit()
            orm_session.refresh(record)
            process_duration = time.time() - start
            metrics.database_operation_duration_seconds.labels(
                operation="save", table="sessions"
            ).observe(process_duration)
            return PostgresMapper.map_record_to_session(record)

    def update(self, session: Session) -> Session:
        self.logger.debug(
            f"Update session {session.id} with version {session.version - 1} to version {session.version}")
        with OrmSession(self.postgres_engine) as orm_session:
            start = time.time()
            existing_record = orm_session.query(SessionRecord).filter(and_(
                SessionRecord.session_id == session.id, SessionRecord.version == session.version - 1)
            ).one_or_none()

            if not existing_record:
                raise OptimisticLockingFailureException(
                    f"Session with id {session.id} was modified by another transaction, ",
                    f"expected version {session.version - 1}")

            updated_record = PostgresMapper.update_record_from_session(existing_record, session)

            orm_session.commit()
            orm_session.refresh(updated_record)
            process_duration = time.time() - start
            metrics.database_operation_duration_seconds.labels(
                operation="update", table="sessions"
            ).observe(process_duration)
            return PostgresMapper.map_record_to_session(updated_record)

    def find_by_id(self, session_id: str) -> Session | None:
        with OrmSession(self.postgres_engine) as orm_session:
            start = time.time()
            record = orm_session.query(SessionRecord).filter(SessionRecord.session_id == session_id).one_or_none()
            if record:
                process_duration = time.time() - start
                metrics.database_operation_duration_seconds.labels(
                    operation="find_by_id", table="sessions"
                ).observe(process_duration)
                return PostgresMapper.map_record_to_session(record)
            return None

    def find_active_session(self) -> Session | None:
        with OrmSession(self.postgres_engine) as orm_session:
            start = time.time()
            record = orm_session.query(SessionRecord).filter(and_(
                SessionRecord.status == Status.DRAFT.value, SessionRecord.end_time.is_(None))).one_or_none()
            if record:
                process_duration = time.time() - start
                metrics.database_operation_duration_seconds.labels(
                    operation="find_active_session", table="sessions"
                ).observe(process_duration)
                return PostgresMapper.map_record_to_session(record)
            return None

    def find_latest_by_type_and_status(self, session_type: Type, session_status: Status) -> Session | None:
        with OrmSession(self.postgres_engine) as orm_session:
            start = time.time()
            record = orm_session.query(SessionRecord).filter(
                and_(SessionRecord.type == session_type.value, SessionRecord.status == session_status.value)).order_by(
                SessionRecord.start_time.desc()).first()
            if record:
                process_duration = time.time() - start
                metrics.database_operation_duration_seconds.labels(
                    operation="find_latest_by_type_and_status", table="sessions"
                ).observe(process_duration)
                return PostgresMapper.map_record_to_session(record)
            return None
