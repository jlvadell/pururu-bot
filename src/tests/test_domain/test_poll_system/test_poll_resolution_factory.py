from unittest.mock import Mock

import pytest
from hamcrest import assert_that, instance_of, equal_to

from pururu.domain.exceptions import PururuException
from pururu.domain.entities import PollResolutionType
from pururu.domain.poll_system.poll_resolution_factory import PollResolutionFactory
from pururu.domain.poll_system.poll_resolution_strategy import SendMessagePollResolution


def set_up():
    return PollResolutionFactory(Mock())


def test_gest_strategy_send_message_resolution():
    # Given
    poll_resolution_factory = set_up()
    # When
    result = poll_resolution_factory.get_strategy(PollResolutionType.SEND_MESSAGE)
    # Then
    assert_that(result, instance_of(SendMessagePollResolution))


def test_gest_strategy_unknown():
    # Given
    poll_resolution_factory = set_up()
    # When/Then
    with pytest.raises(PururuException) as exc_info:
        poll_resolution_factory.get_strategy("unknown")

    assert_that(exc_info.value.args[0], equal_to("Unknown resolution type: unknown"))
