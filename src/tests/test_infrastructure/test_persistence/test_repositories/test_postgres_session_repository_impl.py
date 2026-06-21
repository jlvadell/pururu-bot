from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, equal_to, none
from sqlalchemy.orm import Session as OrmSession

from pururu.domain.entities.session import Session, Status, Type
from pururu.domain.exceptions import OptimisticLockingFailureException
from pururu.infrastructure.adapters.postgres.entities import SessionRecord
from pururu.infrastructure.persistence.repositories.postgres_session_repository_impl import \
    PostgresSessionRepositoryImpl
from tests.test_domain.conftest import session


@pytest.fixture
def mock_engine():
    """Create a mock PostgresDBEngine"""
    mock = MagicMock()
    mock.get_engine.return_value = MagicMock()
    return mock


@pytest.fixture
def repository(mock_engine):
    """Create a PostgresSessionRepositoryImpl instance"""
    return PostgresSessionRepositoryImpl(mock_engine)


@pytest.fixture
def mock_orm_session():
    """Create a mock ORM Session"""
    return MagicMock(spec=OrmSession)


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.OrmSession')
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.PostgresMapper')
def test_save_creates_new_session(mock_mapper, mock_orm_session_class, repository, session):
    """Test save creates a new session in database"""
    # Arrange
    mock_session_context = MagicMock()
    mock_orm_session_class.return_value.__enter__.return_value = mock_session_context

    mock_record = MagicMock(spec=SessionRecord)
    mock_mapper.map_session_to_record.return_value = mock_record
    mock_mapper.map_record_to_session.return_value = session

    # Act
    result = repository.save(session)

    # Assert
    mock_mapper.map_session_to_record.assert_called_once_with(session)
    mock_session_context.add.assert_called_once_with(mock_record)
    mock_session_context.commit.assert_called_once()
    mock_session_context.refresh.assert_called_once_with(mock_record)
    assert_that(result, equal_to(session))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.OrmSession')
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.PostgresMapper')
def test_update_with_correct_version(mock_mapper, mock_orm_session_class, repository):
    """Test update succeeds with correct version"""
    # Arrange
    mock_session_context = MagicMock()
    mock_orm_session_class.return_value.__enter__.return_value = mock_session_context

    existing_record = MagicMock(spec=SessionRecord)
    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = existing_record

    updated_session = Session(
        id="session123",
        season_id="season456",
        type=Type.OFFICIAL_GAME,
        status=Status.COMPLETED,
        players=[],
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=datetime(2025, 10, 1, 12, 0, 0),
        version=2
    )

    mock_mapper.update_record_from_session.return_value = existing_record
    mock_mapper.map_record_to_session.return_value = updated_session

    # Act
    result = repository.update(updated_session)

    # Assert
    mock_mapper.update_record_from_session.assert_called_once_with(existing_record, updated_session)
    mock_session_context.commit.assert_called_once()
    mock_session_context.refresh.assert_called_once_with(existing_record)
    assert_that(result, equal_to(updated_session))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.OrmSession')
def test_update_raises_optimistic_locking_exception(mock_orm_session_class, repository):
    """Test update raises OptimisticLockingFailureException when version mismatch"""
    # Arrange
    mock_session_context = MagicMock()
    mock_orm_session_class.return_value.__enter__.return_value = mock_session_context

    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = None  # No record found

    session = Session(
        id="session123",
        season_id="season456",
        type=Type.OFFICIAL_GAME,
        status=Status.COMPLETED,
        players=[],
        start_time=datetime(2025, 10, 1, 10, 0, 0),
        end_time=datetime(2025, 10, 1, 12, 0, 0),
        version=2
    )

    # Act & Assert
    with pytest.raises(OptimisticLockingFailureException):
        repository.update(session)


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.OrmSession')
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.PostgresMapper')
def test_find_by_id_returns_session(mock_mapper, mock_orm_session_class, repository, session):
    """Test find_by_id returns session when found"""
    # Arrange
    mock_session_context = MagicMock()
    mock_orm_session_class.return_value.__enter__.return_value = mock_session_context

    mock_record = MagicMock(spec=SessionRecord)
    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = mock_record
    mock_mapper.map_record_to_session.return_value = session

    # Act
    result = repository.find_by_id("session123")

    # Assert
    mock_mapper.map_record_to_session.assert_called_once_with(mock_record)
    assert_that(result, equal_to(session))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.OrmSession')
def test_find_by_id_returns_none(mock_orm_session_class, repository):
    """Test find_by_id returns None when not found"""
    # Arrange
    mock_session_context = MagicMock()
    mock_orm_session_class.return_value.__enter__.return_value = mock_session_context

    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = None

    # Act
    result = repository.find_by_id("nonexistent")

    # Assert
    assert_that(result, none())


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.OrmSession')
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.PostgresMapper')
def test_find_active_session_returns_session(mock_mapper, mock_orm_session_class, repository, session):
    """Test find_active_session returns active session"""
    # Arrange
    mock_session_context = MagicMock()
    mock_orm_session_class.return_value.__enter__.return_value = mock_session_context

    mock_record = MagicMock(spec=SessionRecord)
    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = mock_record
    mock_mapper.map_record_to_session.return_value = session

    # Act
    result = repository.find_active_session()

    # Assert
    mock_mapper.map_record_to_session.assert_called_once_with(mock_record)
    assert_that(result, equal_to(session))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.OrmSession')
def test_find_active_session_returns_none(mock_orm_session_class, repository):
    """Test find_active_session returns None when no active session"""
    # Arrange
    mock_session_context = MagicMock()
    mock_orm_session_class.return_value.__enter__.return_value = mock_session_context

    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.one_or_none.return_value = None

    # Act
    result = repository.find_active_session()

    # Assert
    assert_that(result, none())


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.OrmSession')
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.PostgresMapper')
def test_find_latest_by_type_and_status(mock_mapper, mock_orm_session_class, repository):
    """Test find_latest_by_type_and_status returns session when found"""
    # Arrange
    mock_session_context = MagicMock()
    mock_orm_session_class.return_value.__enter__.return_value = mock_session_context

    mock_record = MagicMock(spec=SessionRecord)
    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.order_by.return_value.first.return_value = mock_record
    expected_session = MagicMock(spec=Session)
    mock_mapper.map_record_to_session.return_value = expected_session

    # Act
    result = repository.find_latest_by_type_and_status(Type.OFFICIAL_GAME, Status.COMPLETED)

    # Assert
    mock_mapper.map_record_to_session.assert_called_once_with(mock_record)
    assert_that(result, equal_to(expected_session))


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.OrmSession')
def test_find_latest_by_type_and_status_not_found(mock_orm_session_class, repository):
    """Test find_latest_by_type_and_status returns None when nothing found"""
    # Arrange
    mock_session_context = MagicMock()
    mock_orm_session_class.return_value.__enter__.return_value = mock_session_context

    mock_query = mock_session_context.query.return_value
    mock_query.filter.return_value.order_by.return_value.first.return_value = None

    # Act
    result = repository.find_latest_by_type_and_status(Type.OFFICIAL_GAME, Status.COMPLETED)

    # Assert
    assert_that(result, none())


@pytest.mark.unit
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.OrmSession')
@patch('pururu.infrastructure.persistence.repositories.postgres_session_repository_impl.PostgresMapper')
def test_find_completed_by_player_id(mock_mapper, mock_orm_session_class, repository, session):
    mock_session_context = MagicMock()
    mock_orm_session_class.return_value.__enter__.return_value = mock_session_context
    records = [MagicMock(spec=SessionRecord), MagicMock(spec=SessionRecord)]
    query = mock_session_context.query.return_value
    query.join.return_value.filter.return_value.order_by.return_value.all.return_value = records
    mock_mapper.map_record_to_session.side_effect = [session, session]

    result = repository.find_completed_by_player_id("player123", "excluded")

    query.join.assert_called_once()
    assert_that(result, equal_to([session, session]))
    assert_that(mock_mapper.map_record_to_session.call_count, equal_to(2))
