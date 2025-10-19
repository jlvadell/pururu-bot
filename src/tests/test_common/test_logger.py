import asyncio
import json
import logging
from unittest.mock import patch, MagicMock

import pytest
from hamcrest import assert_that, equal_to, has_key, instance_of, not_none, is_

from pururu.common import logger
from pururu.common.logger import JSONFormatter, get_logger, generate_trace_id, generate_span_id, set_trace_context


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
@pytest.mark.unit
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


@pytest.mark.unit
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
@pytest.mark.unit
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
@pytest.mark.unit
@patch('pururu.common.logger.setup_logging')
@patch('logging.getLogger')
def test_get_logger_calls_setup_and_returns_logger(mock_logging_get_logger, mock_setup_logging):
    """Test get_logger initializes logging and returns logger instance"""
    # Arrange
    mock_logger = MagicMock()
    mock_logging_get_logger.return_value = mock_logger

    # Act
    result = get_logger("test.module")

    # Assert
    mock_setup_logging.assert_called_once()
    mock_logging_get_logger.assert_called_once_with("test.module")
    assert_that(result, equal_to(mock_logger))


# ============================================================================
# Trace Context Tests
# ============================================================================

@pytest.mark.unit
def test_set_trace_context_sets_trace_and_span_ids():
    """Test set_trace_context sets both trace_id and span_id"""
    # Arrange
    trace_id = "abc123def456"
    span_id = "xyz789"

    # Act
    set_trace_context(trace_id, span_id)

    # Assert
    assert_that(logger.trace_id_var.get(), equal_to(trace_id))
    assert_that(logger.span_id_var.get(), equal_to(span_id))


@pytest.mark.unit
def test_set_trace_context_generates_span_id_if_not_provided():
    """Test set_trace_context auto-generates span_id when not provided"""
    # Arrange
    trace_id = "abc123def456"

    # Act
    set_trace_context(trace_id)

    # Assert
    assert_that(logger.trace_id_var.get(), equal_to(trace_id))
    span_id = logger.span_id_var.get()
    assert_that(span_id, not_none())
    assert_that(len(span_id), equal_to(16))


@pytest.mark.unit
@patch('pururu.common.logger.get_version')
def test_json_formatter_includes_trace_context(mock_get_version):
    """Test JSONFormatter includes trace_id and span_id from context"""
    # Arrange
    mock_get_version.return_value = "1.0.0"
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=1,
        msg="test message", args=(), exc_info=None
    )
    
    trace_id = "test_trace_123"
    span_id = "test_span_456"
    logger.trace_id_var.set(trace_id)
    logger.span_id_var.set(span_id)

    # Act
    result = formatter.format(record)

    # Assert
    parsed = json.loads(result)
    assert_that(parsed["trace_id"], equal_to(trace_id))
    assert_that(parsed["span_id"], equal_to(span_id))


@pytest.mark.unit
@patch('pururu.common.logger.get_version')
def test_json_formatter_handles_missing_trace_context(mock_get_version):
    """Test JSONFormatter handles None trace_id and span_id gracefully"""
    # Arrange
    mock_get_version.return_value = "1.0.0"
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=1,
        msg="test message", args=(), exc_info=None
    )
    
    # Clear trace context
    logger.trace_id_var.set(None)
    logger.span_id_var.set(None)

    # Act
    result = formatter.format(record)

    # Assert
    parsed = json.loads(result)
    assert_that(parsed["trace_id"], is_(None))
    assert_that(parsed["span_id"], is_(None))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trace_context_isolation_between_concurrent_tasks():
    """Test trace context maintains separate values across concurrent async tasks"""
    # Arrange
    results = {}

    async def task_with_trace(task_id: str, trace_id: str):
        """Simulates an async task with its own trace context"""
        set_trace_context(trace_id)
        await asyncio.sleep(0.1)  # Simulate async work
        # Check trace_id is still correct after awaiting
        current_trace = logger.trace_id_var.get()
        results[task_id] = current_trace
        return current_trace

    # Act - Run multiple tasks concurrently
    trace1 = "trace_abc123"
    trace2 = "trace_def456"
    trace3 = "trace_ghi789"
    
    task1 = task_with_trace("task1", trace1)
    task2 = task_with_trace("task2", trace2)
    task3 = task_with_trace("task3", trace3)
    
    await asyncio.gather(task1, task2, task3)

    # Assert - Each task maintained its own trace_id
    assert_that(results["task1"], equal_to(trace1))
    assert_that(results["task2"], equal_to(trace2))
    assert_that(results["task3"], equal_to(trace3))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trace_context_inherits_in_spawned_tasks():
    """Test spawned tasks inherit parent trace context"""
    # Arrange
    parent_trace = "parent_trace_123"
    child_result = {}

    async def child_task():
        """Child task should inherit parent's trace context"""
        await asyncio.sleep(0.05)
        child_result["trace_id"] = logger.trace_id_var.get()

    async def parent_task():
        """Parent task sets trace context and spawns child"""
        set_trace_context(parent_trace)
        await child_task()
        return logger.trace_id_var.get()

    # Act
    parent_result = await parent_task()

    # Assert - Child inherited parent's trace_id
    assert_that(parent_result, equal_to(parent_trace))
    assert_that(child_result["trace_id"], equal_to(parent_trace))
