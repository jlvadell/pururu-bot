import logging
from datetime import datetime
from unittest.mock import patch

from freezegun import freeze_time
from hamcrest import assert_that, equal_to

import pururu.utils as utils


@patch("pururu.config.LOG_LEVEL", "DEBUG")
def test_get_logger():
    # Given-When
    actual = utils.get_logger("name")
    # Then
    assert_that(actual.name, equal_to("name"))
    assert_that(actual.getEffectiveLevel(), equal_to(logging.DEBUG))


@freeze_time("2021-09-01 12:00:00")
def test_get_current_time_formatted():
    # Given-When
    actual = utils.get_current_time_formatted()
    # Then
    assert_that(actual, equal_to("2021-09-01 12:00:00"))


def test_format_time():
    # Given
    time = datetime(2021, 9, 1, 12)
    # When
    actual = utils.format_time(time)
    # Then
    assert_that(actual, equal_to("2021-09-01 12:00:00"))


def test_parse_time():
    # Given
    time = "2021-09-01 12:00:00"
    # When
    actual = utils.parse_time(time)
    # Then
    assert_that(actual, equal_to(datetime(2021, 9, 1, 12)))
