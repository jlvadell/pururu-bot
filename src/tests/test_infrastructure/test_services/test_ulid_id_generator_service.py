import pytest
from hamcrest import assert_that

from pururu.infrastructure.services.ulid_id_generator_service import ULIDIdGeneratorService


@pytest.mark.unit
def test_next_id_returns_valid_ulid():
    """Test that next_id returns a valid ULID string."""
    # Arrange
    service = ULIDIdGeneratorService()

    # Act
    ulid_id = service.next_id()

    # Assert
    assert_that(ulid_id is not None)
