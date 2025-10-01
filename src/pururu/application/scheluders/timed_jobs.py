from apscheduler.schedulers.background import BackgroundScheduler

from pururu.application.handlers.background_event_handler import BackgroundEventHandler
from pururu.common import logger


class ScheduledJobs:
    def __init__(self, event_handler: BackgroundEventHandler):
        self.scheduler = BackgroundScheduler()
        self.event_handler = event_handler
        self.logger = logger.get_logger(__name__)

        # ------------------------------------
        # Scheduled tasks
        # ------------------------------------
        self.scheduler.add_job(self.check_expired_polls_task, 'interval', hours=2)

    def start(self) -> None:
        """
        Starts the scheduler
        :return: None
        """
        self.logger.info(f"Starting scheduler, jobs: {len(self.scheduler.get_jobs())}",
                         extra={"job_count": len(self.scheduler.get_jobs())})
        self.scheduler.start()

    def stop(self) -> None:
        """
        Stops the scheduler
        :return: None
        """
        self.logger.info("Stopping scheduler")
        self.scheduler.shutdown(wait=False)

    def check_expired_polls_task(self) -> None:
        """
        Emits the CHECK_EXPIRED_POLLS event
        :return: None
        """
        self.logger.debug("Triggering check expired polls flow")
        self.event_handler.trigger_check_expired_polls_flow()
