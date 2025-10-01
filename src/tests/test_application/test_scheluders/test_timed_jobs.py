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
def test_check_expired_polls_task_triggers_flow():
    """Test check_expired_polls_task"""
    # Given
    handler_mock = Mock()
    scheduled_jobs = ScheduledJobs(handler_mock)
    # When
    scheduled_jobs.check_expired_polls_task()
    # Then
    handler_mock.trigger_check_expired_polls_flow.assert_called_once()
