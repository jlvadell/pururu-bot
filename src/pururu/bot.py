import pururu.config as config
import pururu.utils as utils
from pururu.application.events.event_system import EventSystem
from pururu.application.events.listeners import EventListeners
from pururu.domain.services.pururu_service import PururuService
from pururu.infrastructure.adapters.discord.discord_service_adapter import DiscordServiceAdapter
from pururu.infrastructure.adapters.google_sheets.google_sheets_adapter import GoogleSheetsAdapter
from pururu.interface.discord.discord_event_handlers import DiscordEventHandler


class Application:
    def __init__(self):
        self.db_service = None
        self.event_system = None
        self.pururu_service = None
        self.event_listeners = None
        self.discord_event_handler = None
        self.discord_service = None
        self.dc_client = None
        self.logger = utils.get_logger(__name__)

    def init(self):
        # ----------------------------------------
        # -------------- Setup Adapters
        # ----------------------------------------
        # Google Sheet
        self.db_service = GoogleSheetsAdapter(config.GOOGLE_SHEETS_CREDENTIALS, config.SPREADSHEET_ID)
        # Discord.py
        self.discord_service = DiscordServiceAdapter()
        self.dc_client = self.discord_service.get_client()

        # ----------------------------------------
        # -------------- Setup Application services
        # ----------------------------------------
        self.event_system = EventSystem()
        self.pururu_service = PururuService(self.db_service, self.event_system, self.discord_service)
        self.event_listeners = EventListeners(self.event_system, self.pururu_service)

        # ----------------------------------------
        # -------------- Setup Entrypoints
        # ----------------------------------------
        self.discord_event_handler = DiscordEventHandler(self.dc_client, self.pururu_service)

        # ----------------------------------------
        # -------------- RUN APP
        # ----------------------------------------
        self.dc_client.run(config.DISCORD_TOKEN)


if __name__ == '__main__':
    app = Application()
    app.init()
