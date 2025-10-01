import json
import logging
from unittest.mock import patch, MagicMock

import pytest
from hamcrest import assert_that, equal_to, has_key, instance_of

from pururu.common.logger import JSONFormatter, get_logger


@pytest.fixture
def log_record():
    """Create a sample log record for testing"""
    return logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="/path/to/file.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )


# Test JSONFormatter
@patch('pururu.common.logger.get_version')
def test_json_formatter_creates_valid_json_with_required_fields(mock_get_version, log_record):
    # Arrange
    mock_get_version.return_value = "1.2.3"
    formatter = JSONFormatter()

    # Act
    result = formatter.format(log_record)

    # Assert
    parsed = json.loads(result)
    assert_that(parsed, has_key("timestamp"))
    assert_that(parsed["level"], equal_to("INFO"))
    assert_that(parsed["source"], equal_to("test.logger"))
    assert_that(parsed["message"], equal_to("Test message"))
    assert_that(parsed["app_version"], equal_to("1.2.3"))


@patch('pururu.common.logger.get_version')
def test_json_formatter_includes_extra_fields(mock_get_version):
    # Arrange
    mock_get_version.return_value = "1.0.0"
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=1,
        msg="test", args=(), exc_info=None
    )
    record.user_id = "user123"
    record.request_id = 789

    # Act
    result = formatter.format(record)

    # Assert
    parsed = json.loads(result)
    assert_that(parsed["user_id"], equal_to("user123"))
    assert_that(parsed["request_id"], equal_to(789))
    assert_that(parsed["app_version"], equal_to("1.0.0"))


# Test setup_logging()
@pytest.mark.parametrize("use_json_format,expected_formatter_type", [
    (True, JSONFormatter),
    (False, logging.Formatter)
])
@patch('pururu.common.logger.settings')
@patch('logging.getLogger')
@patch('logging.StreamHandler')
def test_setup_logging_uses_correct_formatter(mock_stream_handler, mock_get_logger, mock_settings, use_json_format,
                                              expected_formatter_type):
    # Arrange
    mock_settings.general.log_format_json = use_json_format
    mock_settings.general.log_level = logging.INFO
    mock_settings.general.third_party_default_log_level = logging.WARNING

    mock_root_logger = MagicMock()
    mock_get_logger.return_value = mock_root_logger

    mock_handler = MagicMock()
    mock_stream_handler.return_value = mock_handler

    # Reset global state
    import pururu.common.logger as logger_test
    logger_test._initialized = False

    # Act
    logger_test.setup_logging()

    # Assert
    mock_root_logger.handlers.clear.assert_called_once()
    mock_root_logger.addHandler.assert_called_once_with(mock_handler)

    # Check the formatter that was set
    formatter_call = mock_handler.setFormatter.call_args[0][0]
    assert_that(formatter_call, instance_of(expected_formatter_type))


# Test get_logger()
@patch('pururu.common.logger.setup_logging')
@patch('logging.getLogger')
def test_get_logger_calls_setup_and_returns_logger(mock_logging_get_logger, mock_setup_logging):
    # Arrange
    mock_logger = MagicMock()
    mock_logging_get_logger.return_value = mock_logger

    # Act
    result = get_logger("test.module")

    # Assert
    mock_setup_logging.assert_called_once()
    mock_logging_get_logger.assert_called_once_with("test.module")
    assert_that(result, equal_to(mock_logger))
