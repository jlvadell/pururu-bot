import asyncio
import signal

from pururu.application.handlers.background_event_handler import BackgroundEventHandler
from pururu.application.handlers.discord_event_handler import DiscordEventHandler
from pururu.application.handlers.poll_event_handler import PollEventHandler
from pururu.application.handlers.session_events_handler import SessionEventsHandler
from pururu.application.scheluders.timed_jobs import ScheduledJobs
from pururu.application.watchers.config_watcher import ConfigFilesWatcher
from pururu.common import logger, utils
from pururu.config import settings
from pururu.domain.messaging.event_bus import EventBus
from pururu.domain.repositories.player_repository import PlayerRepository
from pururu.domain.repositories.poll_repository import PollRepository
from pururu.domain.repositories.season_repository import SeasonRepository
from pururu.domain.repositories.session_repository import SessionRepository
from pururu.domain.services.data_sync_service import DataSyncService
from pururu.domain.services.discord_service import DiscordService
from pururu.domain.services.id_generator_service import IdGeneratorService
from pururu.domain.services.player_service import PlayerService
from pururu.domain.services.poll_system.poll_resolution_factory import PollResolutionFactory
from pururu.domain.services.poll_system.poll_system_service import PollSystemService
from pururu.domain.services.season_service import SeasonService
from pururu.domain.services.session_service import SessionService
from pururu.infrastructure.adapters.aws.sns_client_adapter import SNSClientAdapter
from pururu.infrastructure.adapters.aws.sqs_client_adapter import SQSClientAdapter
from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot
from pururu.infrastructure.adapters.google_sheets.google_sheets_adapter import GoogleSheetsAdapter
from pururu.infrastructure.adapters.postgres.engine import PostgresDBEngine
from pururu.infrastructure.messaging.aws_event_bus import AWSEventBus
from pururu.infrastructure.persistence.repositories.postgres_player_repository_impl import PostgresPlayerRepositoryImpl
from pururu.infrastructure.persistence.repositories.postgres_poll_repository_impl import PostgresPollRepositoryImpl
from pururu.infrastructure.persistence.repositories.postgres_season_repository_impl import PostgresSeasonRepositoryImpl
from pururu.infrastructure.persistence.repositories.postgres_session_repository_impl import \
    PostgresSessionRepositoryImpl
from pururu.infrastructure.services.data_sync_service_impl import DataSyncServiceImpl
from pururu.infrastructure.services.discord_service_impl import DiscordServiceImpl
from pururu.infrastructure.services.ulid_id_generator_service import ULIDIdGeneratorService


class Application:
    def __init__(self):
        self.sqs_adapter: SQSClientAdapter | None = None
        self.sns_adapter: SNSClientAdapter | None = None
        self.discord_bot: PururuDiscordBot | None = None
        self.google_sheet_adapter: GoogleSheetsAdapter | None = None
        self.postgres_engine: PostgresDBEngine | None = None
        self.event_bus: EventBus | None = None
        self.player_repository: PlayerRepository | None = None
        self.season_repository: SeasonRepository | None = None
        self.session_repository: SessionRepository | None = None
        self.poll_repository: PollRepository | None = None
        self.data_sync_service: DataSyncService | None = None
        self.discord_service: DiscordService | None = None
        self.id_generator_service: IdGeneratorService | None = None
        self.player_service: PlayerService | None = None
        self.season_service: SeasonService | None = None
        self.session_service: SessionService | None = None
        self.poll_resolution_factory: PollResolutionFactory | None = None
        self.poll_system_service: PollSystemService | None = None
        self.background_event_handler: BackgroundEventHandler | None = None
        self.discord_event_handler: DiscordEventHandler | None = None
        self.poll_event_handler: PollEventHandler | None = None
        self.session_events_handler: SessionEventsHandler | None = None
        self.scheduler: ScheduledJobs | None = None
        self.config_watcher: ConfigFilesWatcher | None = None
        self.logger = logger.get_logger(__name__)

    async def init(self):
        self.logger.info(utils.get_banner())
        self.logger.info("Initializing")

        # --------------------------------
        # INFRASTRUCTURE
        # --------------------------------
        # Adapters
        self.sqs_adapter = SQSClientAdapter()
        self.sns_adapter = SNSClientAdapter()
        self.discord_bot = PururuDiscordBot()
        self.google_sheet_adapter = GoogleSheetsAdapter(settings.secrets.google_sheets_credentials,
                                                        settings.secrets.spreadsheet_id)
        self.postgres_engine = PostgresDBEngine(settings.database.postgres.protocol,
                                                settings.secrets.postgres_user,
                                                settings.secrets.postgres_password,
                                                settings.database.postgres.host,
                                                settings.database.postgres.port,
                                                settings.database.postgres.database)

        # Messaging
        self.event_bus = AWSEventBus(self.sns_adapter, self.sqs_adapter)

        # Repositories
        self.player_repository = PostgresPlayerRepositoryImpl(self.postgres_engine)
        self.season_repository = PostgresSeasonRepositoryImpl(self.postgres_engine)
        self.session_repository = PostgresSessionRepositoryImpl(self.postgres_engine)
        self.poll_repository = PostgresPollRepositoryImpl(self.postgres_engine)

        # Services implementations
        self.data_sync_service = DataSyncServiceImpl(self.google_sheet_adapter)
        self.discord_service = DiscordServiceImpl(self.discord_bot)
        self.id_generator_service = ULIDIdGeneratorService()

        # --------------------------------
        # DOMAIN
        # --------------------------------
        # Services
        self.player_service = PlayerService(self.player_repository)
        self.season_service = SeasonService(self.season_repository)
        self.session_service = SessionService(self.session_repository, self.season_service, self.player_service,
                                              self.id_generator_service, self.event_bus)
        self.poll_resolution_factory = PollResolutionFactory(self.discord_service)
        self.poll_system_service = PollSystemService(self.poll_repository, self.discord_service,
                                                     self.poll_resolution_factory)

        # --------------------------------
        # APPLICATION
        # --------------------------------
        # Handlers
        self.background_event_handler = BackgroundEventHandler(self.event_bus)
        self.discord_event_handler = DiscordEventHandler(self.event_bus)
        self.poll_event_handler = PollEventHandler(self.event_bus, self.poll_system_service)
        self.session_events_handler = SessionEventsHandler(self.session_service, self.data_sync_service, self.event_bus, self.discord_service)

        # Schedulers
        self.scheduler = ScheduledJobs(self.background_event_handler)

        # Watchers
        self.config_watcher = ConfigFilesWatcher(self.background_event_handler)

        # --------------------------------
        # ADDITIONAL WIRING
        # --------------------------------
        # Discord event handler registration
        self.discord_bot.set_event_handler(self.discord_event_handler)

        # --------------------------------
        # STARTUP
        # --------------------------------
        self.logger.info("Starting application.......")

        self.scheduler.start() # start scheduled jobs
        self.config_watcher.start_config_watcher() # start config file watcher
        self.sqs_adapter.start_polling() # start SQS polling

        # start async processes
        try:
            await self.discord_bot.start(settings.secrets.discord_token)
        except asyncio.CancelledError:
            await self.shutdown()
            raise

    async def shutdown(self):
        self.logger.info("Stopping application.......")
        self.logger.info("Cancelling background tasks")
        if self.sqs_adapter:
            self.sqs_adapter.stop_polling()
            self.logger.info("SQS polling stopped")
        if self.scheduler:
            self.scheduler.stop()
            self.logger.info("Scheduler stopped")
        if self.config_watcher:
            self.config_watcher.stop_config_watcher()
            self.logger.info("Config watcher stopped")
        await self.discord_bot.close()
        self.logger.info("Discord connection closed")
        self.logger.info("Application stopped")


def main():
    """Main entry point for the application."""
    app = Application()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.ensure_future(app.shutdown()))
        except NotImplementedError:
            """Handle NotImplementedError on Windows"""
            pass
    try:
        loop.run_until_complete(app.init())
    except KeyboardInterrupt:
        loop.run_until_complete(app.shutdown())
    finally:
        loop.close()


if __name__ == '__main__':
    main()
