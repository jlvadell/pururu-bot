from unittest.mock import Mock, patch

from pururu.application.scheluders.timed_jobs import ScheduledJobs


@patch("apscheduler.schedulers.background.BackgroundScheduler.add_job")
def test_scheduler_initialization(mock_add_job):
    # Given
    scheduled_jobs = ScheduledJobs(pururu_handler=Mock())
    # When-Then
    mock_add_job.assert_called_once_with(
        scheduled_jobs.check_expired_polls_task,
        'interval',
        minute=1
    )


def test_scheduler_start():
    # Given
    scheduled_jobs = ScheduledJobs(pururu_handler=Mock())
    scheduled_jobs.scheduler = Mock()
    # When
    scheduled_jobs.start()
    # Then
    scheduled_jobs.scheduler.start.assert_called_once()


def test_check_expired_polls_task_triggers_flow():
    # Given
    handler_mock = Mock()
    scheduled_jobs = ScheduledJobs(pururu_handler=handler_mock)
    # When
    scheduled_jobs.check_expired_polls_task()
    # Then
    handler_mock.trigger_check_expired_polls_flow.assert_called_once()
