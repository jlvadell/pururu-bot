from datetime import datetime

import pytest
from hamcrest import assert_that, equal_to

from pururu.domain.entities.poll import Poll, PollResolutionType


@pytest.mark.unit
def test_get_winners_single_winner():
    """Test get_winners returns single winner"""
    # Arrange
    poll = Poll(
        id="poll123",
        channel_id="channel456",
        expires_at=datetime(2025, 10, 2, 12, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE,
        question="What game?",
        answers=["Game A", "Game B", "Game C"],
        results={"Game A": 5, "Game B": 3, "Game C": 2}
    )

    # Act
    result = poll.get_winners()

    # Assert
    assert_that(result, equal_to("Game A"))


@pytest.mark.unit
def test_get_winners_multiple_winners_tie():
    """Test get_winners returns multiple winners when tied"""
    # Arrange
    poll = Poll(
        id="poll123",
        channel_id="channel456",
        expires_at=datetime(2025, 10, 2, 12, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE,
        question="What game?",
        answers=["Game A", "Game B", "Game C"],
        results={"Game A": 5, "Game B": 5, "Game C": 2}
    )

    # Act
    result = poll.get_winners()

    # Assert
    assert_that(result, equal_to("Game A, Game B"))


@pytest.mark.unit
def test_get_winners_all_tied():
    """Test get_winners returns all answers when all tied"""
    # Arrange
    poll = Poll(
        id="poll123",
        channel_id="channel456",
        expires_at=datetime(2025, 10, 2, 12, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE,
        question="What game?",
        answers=["Game A", "Game B", "Game C"],
        results={"Game A": 3, "Game B": 3, "Game C": 3}
    )

    # Act
    result = poll.get_winners()

    # Assert
    assert_that(result, equal_to("Game A, Game B, Game C"))


@pytest.mark.unit
def test_get_winners_with_zero_votes():
    """Test get_winners when all answers have zero votes"""
    # Arrange
    poll = Poll(
        id="poll123",
        channel_id="channel456",
        expires_at=datetime(2025, 10, 2, 12, 0, 0),
        resolution_type=PollResolutionType.SEND_MESSAGE,
        question="What game?",
        answers=["Game A", "Game B"],
        results={"Game A": 0, "Game B": 0}
    )

    # Act
    result = poll.get_winners()

    # Assert
    assert_that(result, equal_to("Game A, Game B"))
