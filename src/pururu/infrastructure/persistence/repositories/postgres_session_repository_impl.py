from sqlalchemy import and_
from sqlalchemy.orm import Session as OrmSession

from pururu.common import logger
from pururu.domain.entities.session import Session, Status
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
            orm_session.add(record)
            orm_session.commit()
            orm_session.refresh(record)
            return PostgresMapper.map_record_to_session(record)

    def update(self, session: Session) -> Session:
        self.logger.warning(
            f"Update session {session.id} with version {session.version - 1} to version {session.version}")
        with OrmSession(self.postgres_engine) as orm_session:
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
            return PostgresMapper.map_record_to_session(updated_record)

    def find_by_id(self, session_id: str) -> Session | None:
        with OrmSession(self.postgres_engine) as orm_session:
            record = orm_session.query(SessionRecord).filter(SessionRecord.session_id == session_id).one_or_none()
            if record:
                return PostgresMapper.map_record_to_session(record)
            return None

    def find_active_session(self) -> Session | None:
        with OrmSession(self.postgres_engine) as orm_session:
            record = orm_session.query(SessionRecord).filter(
                SessionRecord.status == Status.DRAFT.value and SessionRecord.end_time == None).one_or_none()
            if record:
                return PostgresMapper.map_record_to_session(record)
            return None
