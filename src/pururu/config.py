import json
import os

from dotenv import load_dotenv
import pururu.__version__ as version

# ----------------------------------------
# -------------- Load env files
# ----------------------------------------
load_dotenv('pururu/.env.base')

env = os.getenv('APP_ENV', 'development')

if env in ['production', 'development']:
    dotenv_file = f'pururu/.env.{env}'
    load_dotenv(dotenv_file, override=True, verbose=True)

# ----------------------------------------
# -------------- Application configs
# ----------------------------------------
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
ATTENDANCE_CHECK_DELAY = int(os.getenv('ATTENDANCE_CHECK_DELAY', 120))  # defaults to 2 minutes
MIN_ATTENDANCE_TIME = int(os.getenv('MIN_ATTENDANCE_TIME', 1800))  # defaults to 30 minutes
PLAYERS = os.getenv('PLAYERS').split(',') if os.getenv('PLAYERS') else []
MIN_ATTENDANCE_MEMBERS = int(os.getenv('MIN_ATTENDANCE_MEMBERS', 3))
PING_MESSAGE = os.getenv('PING_MESSAGE', '')
EVENT_CONCURRENCY_TIME = os.getenv('EVENT_CONCURRENCY_TIME', 20) #minimum amount of time in seconds allowed between events
EVENT_DELAY_TIME = os.getenv('EVENT_DELAY_TIME', 20) #delay time

# ----------------------------------------
# -------------- Discord configs
# ----------------------------------------
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))

# ----------------------------------------
# -------------- GS Adapter configs
# ----------------------------------------
GOOGLE_SHEETS_CREDENTIALS = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
GS_ATTENDANCE_PLAYER_MAPPING = json.loads(os.getenv('GS_ATTENDANCE_PLAYER_MAPPING')) \
    if os.getenv('GS_ATTENDANCE_PLAYER_MAPPING') else {}

# ----------------------------------------
# -------------- APP Metadata
# ----------------------------------------
APP_VERSION = version.__version__
