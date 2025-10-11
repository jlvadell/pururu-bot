from sqlalchemy import create_engine, NullPool, Engine

from pururu.common import logger
from pururu.config import settings
from .entities import Base


class PostgresDBEngine:
    def __init__(self, protocol: str, user: str, password: str, host: str, port: int, db_name: str):
        """
        Initializes the PostgresDBEngine with an SQLAlchemy engine.
        Async note: using sync for simplicity, as in the current implementation, async would not bring benefits and would make the testing and querying more complex.
        :param protocol: the database protocol, e.g., 'postgresql+psycopg2'
        :param user: the database user, e.g., 'postgres'
        :param password: the database password, e.g., 'password'
        :param host: the database host, e.g., 'localhost'
        :param port: the database port, e.g., 5432
        :param db_name: the database name, e.g., 'mydatabase'
        """
        db_url = f"{protocol}://{user}:{password}@{host}:{port}/{db_name}"
        # Ref: https://supabase.com/docs/guides/troubleshooting/using-sqlalchemy-with-supabase-FUqebT
        self.engine = create_engine(db_url, echo=settings.database.postgres.echo, poolclass=NullPool)
        self.logger = logger.get_logger(__name__)
        self.load_metadata()

    def get_engine(self) -> Engine:
        """
        Returns the SQLAlchemy engine instance.
        :return: SQLAlchemy Engine
        """
        return self.engine

    def load_metadata(self) -> None:
        """
        Loads the metadata for the given base.
        :param base: The declarative base containing the metadata.
        """
        self.logger.info("Loading database metadata...")
        Base.metadata.create_all(self.engine)
        self.logger.info("Database metadata loaded successfully.")
