import pururu.config as config
import pururu.utils as utils
from pururu.application.events.listeners import EventListeners
from pururu.application.scheluders.timed_jobs import ScheduledJobs
from pururu.application.events.event_system import EventSystem
from pururu.application.services.pururu_handler import PururuHandler
from pururu.domain.services.pururu_service import PururuService
from pururu.infrastructure.adapters.discord.discord_bot import PururuDiscordBot
from pururu.infrastructure.adapters.discord.discord_service_adapter import DiscordServiceAdapter
from pururu.infrastructure.adapters.google_sheets.google_sheets_adapter import GoogleSheetsAdapter


class Application:
    def __init__(self):
        self.db_service = None
        self.event_system = None
        self.event_system_listeners = None
        self.pururu_service = None
        self.pururu_handler = None
        self.discord_service = None
        self.discord_bot = None
        self.scheduler = None
        self.logger = utils.get_logger(__name__)

    def init(self):
        # Event System
        self.event_system = EventSystem()

        # Google Sheet - Database service implementation
        self.db_service = GoogleSheetsAdapter(config.GOOGLE_SHEETS_CREDENTIALS, config.SPREADSHEET_ID)

        # Domain service
        self.pururu_service = PururuService(self.db_service)

        # Application service
        self.pururu_handler = PururuHandler(self.pururu_service, self.event_system)

        # Scheduled Jobs
        self.scheduler = ScheduledJobs(self.pururu_handler)

        # Event Listeners
        self.event_system_listeners = EventListeners(self.event_system, self.pururu_handler)

        # Discord.py bot integration
        self.discord_bot = PururuDiscordBot(self.pururu_handler)

        # Discord Service - Adapter implementation
        self.discord_service = DiscordServiceAdapter(self.discord_bot)

        # Additional wiring
        self.pururu_service.set_discord_service(self.discord_service)
        self.scheduler.start()

        # Run Application
        self.discord_bot.run(config.DISCORD_TOKEN)


if __name__ == '__main__':
    app = Application()
    app.init()
