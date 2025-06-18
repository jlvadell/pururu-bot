import pururu.config as config
import asyncio
from pururu.common import utils
from pururu.application.events.event_consumers import GameEventConsumer, PollEventConsumer
from pururu.application.scheluders.timed_jobs import ScheduledJobs
from pururu.application.services.pururu_handler import PururuHandler
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
        self.game_event_consumer = None
        self.poll_event_consumer = None
        self.logger = utils.get_logger(__name__)

    async def init(self):
        # Event Service
        self.event_emitter_service = SNSEventServiceAdapter()

        # Google Sheet - Database service implementation
        self.db_service = GoogleSheetsAdapter(config.GOOGLE_SHEETS_CREDENTIALS, config.SPREADSHEET_ID)

        # Domain service
        self.pururu_service = PururuService(self.db_service)

        # Application service
        self.pururu_handler = PururuHandler(self.pururu_service, self.event_emitter_service)

        # Scheduled Jobs
        self.scheduler = ScheduledJobs(self.pururu_handler)

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
        asyncio.create_task(self.game_event_consumer.start_polling())
        asyncio.create_task(self.poll_event_consumer.start_polling())

        # Run Application
        await self.discord_bot.start(config.DISCORD_TOKEN)


if __name__ == '__main__':
    app = Application()
    asyncio.run(app.init())
