from unittest.mock import Mock, patch

import pytest

from pururu.application.scheluders.timed_jobs import ScheduledJobs


@pytest.mark.unit
@patch("apscheduler.schedulers.background.BackgroundScheduler.add_job")
def test_scheduler_initialization(mock_add_job):
    """Test scheduler initialization"""
    # Given
    scheduled_jobs = ScheduledJobs(Mock())
    # When-Then
    mock_add_job.assert_called_once_with(
        scheduled_jobs.check_expired_polls_task,
        'interval',
        hours=2
    )


@pytest.mark.unit
def test_scheduler_start():
    """Test scheduler start"""
    # Given
    scheduled_jobs = ScheduledJobs(Mock())
    scheduled_jobs.scheduler = Mock()
    scheduled_jobs.scheduler.get_jobs.return_value = []
    # When
    scheduled_jobs.start()
    # Then
    scheduled_jobs.scheduler.start.assert_called_once()


@pytest.mark.unit
@patch('pururu.application.scheluders.timed_jobs.logger')
def test_check_expired_polls_task_triggers_flow(mock_logger):
    """Test check_expired_polls_task sets trace context"""
    # Arrange
    handler_mock = Mock()
    scheduled_jobs = ScheduledJobs(handler_mock)
    mock_logger.generate_trace_id.return_value = "test_trace_job_666"
    mock_logger.set_trace_context = Mock()
    
    # Act
    scheduled_jobs.check_expired_polls_task()
    
    # Assert
    mock_logger.generate_trace_id.assert_called_once()
    mock_logger.set_trace_context.assert_called_once_with("test_trace_job_666")
    handler_mock.trigger_check_expired_polls_flow.assert_called_once()
