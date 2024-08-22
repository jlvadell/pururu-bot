from unittest.mock import patch

from freezegun import freeze_time
from hamcrest import assert_that, equal_to

from app import utils


@patch("config.LOG_LEVEL", "DEBUG")
def test_get_logger():
    actual = utils.get_logger("name")
    assert_that(actual.name, equal_to("name"))
    assert_that(actual.level, equal_to(10)) # DEBUG

@freeze_time("2021-09-01 12:00:00")
def test_get_current_time_formatted():
    actual = utils.get_current_time_formatted()
    assert_that(actual, equal_to("2021-09-01 12:00:00"))