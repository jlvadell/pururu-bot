from apscheduler.schedulers.background import BackgroundScheduler

import pururu.utils as utils
from pururu.application.services.pururu_handler import PururuHandler


class ScheduledJobs:
    def __init__(self, pururu_handler: PururuHandler):
        self.scheduler = BackgroundScheduler()
        self.pururu_handler = pururu_handler
        self.logger = utils.get_logger(__name__)

        # ------------------------------------
        # Scheduled tasks
        # ------------------------------------
        self.scheduler.add_job(self.check_expired_polls_task, 'interval', hours=2)

    def start(self) -> None:
        """
        Starts the scheduler
        :return: None
        """
        self.logger.info("Starting scheduler")
        self.scheduler.start()

    def check_expired_polls_task(self) -> None:
        """
        Emits the CHECK_EXPIRED_POLLS event
        :return: None
        """
        self.logger.debug("Checking expired polls task")
        self.pururu_handler.trigger_check_expired_polls_flow()
