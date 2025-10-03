from unittest.mock import MagicMock

import pytest
from hamcrest import assert_that, equal_to, instance_of, calling, raises

from pururu.domain.entities.poll import PollResolutionType
from pururu.domain.exceptions import PollResolutionStrategyUnsupportedException
from pururu.domain.services.poll_system.poll_resolution_factory import PollResolutionFactory
from pururu.domain.services.poll_system.poll_resolution_strategy import (PollResolutionStrategy,
                                                                         SendMessagePollResolution)


@pytest.fixture
def mock_discord_service():
    """Create a mock DiscordService"""
    return MagicMock()


@pytest.fixture
def factory(mock_discord_service):
    """Create a PollResolutionFactory instance"""
    return PollResolutionFactory(mock_discord_service)


@pytest.mark.unit
def test_get_strategy_returns_send_message_resolution(factory, mock_discord_service):
    """Test get_strategy returns SendMessagePollResolution for SEND_MESSAGE type"""
    # Arrange
    resolution_type = PollResolutionType.SEND_MESSAGE

    # Act
    result: PollResolutionStrategy = factory.get_strategy(resolution_type)

    # Assert
    assert_that(result, instance_of(SendMessagePollResolution))
    assert_that(result.discord_service, equal_to(mock_discord_service))


@pytest.mark.unit
def test_get_strategy_raises_exception_for_unsupported_type(factory):
    """Test get_strategy raises exception for unsupported resolution type"""
    # Arrange
    unsupported_type = "INVALID_TYPE"

    # Act & Assert
    assert_that(
        calling(factory.get_strategy).with_args(unsupported_type),
        raises(PollResolutionStrategyUnsupportedException)
    )
