import asyncio
import signal

from pururu.application.events.event_consumers import GameEventConsumer, PollEventConsumer
from pururu.application.scheluders.timed_jobs import ScheduledJobs
from pururu.application.services.pururu_handler import PururuHandler
from pururu.application.watchers.config_watcher import ConfigFilesWatcher
from pururu.common import logger, utils
from pururu.config import settings
from pururu.domain.services.pururu_service import PururuService
from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot
from pururu.infrastructure.adapters.discord.discord_service_adapter import DiscordServiceAdapter
from pururu.infrastructure.adapters.google_sheets.google_sheets_adapter import GoogleSheetsAdapter
from pururu.infrastructure.adapters.sns.sns_event_service_adapter import SNSEventServiceAdapter


class Application:
    def __init__(self):
        self.db_service = None
        self.event_emitter_service = None
        self.event_system_listeners = None
        self.pururu_service = None
        self.pururu_handler = None
        self.discord_service = None
        self.discord_bot = None
        self.scheduler = None
        self.config_watcher = None
        self.game_event_consumer = None
        self.poll_event_consumer = None
        self.tasks = []
        self.logger = logger.get_logger(__name__)

    async def init(self):
        self.logger.info(utils.get_banner())
        self.logger.info("Initializing")

        # Event Service
        self.event_emitter_service = SNSEventServiceAdapter()

        # Google Sheet - Database service implementation
        self.db_service = GoogleSheetsAdapter(settings.secrets.google_sheets_credentials,
                                              settings.secrets.spreadsheet_id)

        # Domain service
        self.pururu_service = PururuService(self.db_service)

        # Application service
        self.pururu_handler = PururuHandler(self.pururu_service, self.event_emitter_service)

        # Scheduled Jobs
        self.scheduler = ScheduledJobs(self.pururu_handler)

        # watchers
        self.config_watcher = ConfigFilesWatcher(self.pururu_handler)

        # Event Consumers
        self.game_event_consumer = GameEventConsumer(self.pururu_handler)
        self.poll_event_consumer = PollEventConsumer(self.pururu_handler)

        # Discord.py bot integration
        self.discord_bot = PururuDiscordBot(self.pururu_handler)

        # Discord Service - Adapter implementation
        self.discord_service = DiscordServiceAdapter(self.discord_bot)

        # Additional wiring
        self.pururu_service.set_discord_service(self.discord_service)
        self.scheduler.start()
        self.config_watcher.start_config_watcher()

        # start async processes
        try:
            async with asyncio.TaskGroup() as tg:
                game_consumer = tg.create_task(self.game_event_consumer.start_polling(),
                                               name="GameEventConsumer_polling")
                poll_consumer = tg.create_task(self.poll_event_consumer.start_polling(),
                                               name="PollEventConsumer_polling")
                self.tasks.append(game_consumer)
                self.tasks.append(poll_consumer)
                await self.discord_bot.start(settings.secrets.discord_token)
        except asyncio.CancelledError:
            await self.shutdown()
            raise

    async def shutdown(self):
        self.logger.info("Stopping application.......")
        self.logger.info("Cancelling background tasks")
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                self.logger.debug(f"Task {task.get_name()} was cancelled successfully")
        if self.scheduler:
            self.scheduler.stop()
            self.logger.info("Scheduler stopped")
        if self.config_watcher:
            self.config_watcher.stop_config_watcher()
            self.logger.info("Config watcher stopped")
        await self.discord_bot.close()
        self.logger.info("Discord connection closed")
        self.logger.info("Application stopped")


if __name__ == '__main__':
    app = Application()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.ensure_future(app.shutdown))
        except NotImplementedError:
            """Handle NotImplementedError on Windows"""
            pass
    try:
        loop.run_until_complete(app.init())
    except KeyboardInterrupt:
        loop.run_until_complete(app.shutdown())
    finally:
        loop.close()
