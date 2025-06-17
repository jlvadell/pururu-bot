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
# -------------- Helpers
# ----------------------------------------
def str_to_bool(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes", "y")

# ----------------------------------------
# -------------- Application configs
# ----------------------------------------
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
ATTENDANCE_CHECK_DELAY = int(os.getenv('ATTENDANCE_CHECK_DELAY', 120))  # defaults to 2 minutes
MIN_ATTENDANCE_TIME = int(os.getenv('MIN_ATTENDANCE_TIME', 1800))  # defaults to 30 minutes
PLAYERS = os.getenv('PLAYERS').split(',') if os.getenv('PLAYERS') else []
MIN_ATTENDANCE_MEMBERS = int(os.getenv('MIN_ATTENDANCE_MEMBERS', 3))
PING_MESSAGE = os.getenv('PING_MESSAGE', '')

# ----------------------------------------
# -------------- Event System configs
# ----------------------------------------
EVENT_BACKOFF_BASE = int(os.getenv('EVENT_BACKOFF_BASE', 5)) # backoff base in seconds
EVENT_BACKOFF_MAX = int(os.getenv('EVENT_BACKOFF_MAX', 300)) # backoff max in seconds; 5 minutes
EVENT_MAX_RETRIES = int(os.getenv('EVENT_MAX_RETRIES', 10)) # max retries
GAME_EVENTS_QUEUE_URL = os.getenv('GAME_EVENTS_QUEUE_URL', 'http://localhost:4576/queue/pururu-game-events') # SQS
POLL_EVENTS_QUEUE_URL = os.getenv('POLL_EVENTS_QUEUE_URL', 'http://localhost:4576/queue/pururu-poll-events') # SQS
SQS_EVENT_VISIBILITY_TIMEOUT = int(os.getenv('SQS_EVENT_VISIBILITY_TIMEOUT', 120))  # in seconds; 2 minutes
EVENTS_POLLING_INTERVAL = int(os.getenv('EVENTS_POLLING_INTERVAL', 20))  # in seconds
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN', 'http://localhost:4575/publish/pururu-game-events')  # SNS

# ----------------------------------------
# -------------- Discord configs
# ----------------------------------------
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))
DISCORD_EVENT_LOG_CHANNEL_ID = int(os.getenv('DISCORD_EVENT_LOG_CHANNEL_ID', 0))
DISCORD_EVENT_LOG_ENABLED = str_to_bool(os.getenv('DISCORD_EVENT_LOG_ENABLED', 'false'))

# ----------------------------------------
# -------------- GS Adapter configs
# ----------------------------------------
GOOGLE_SHEETS_CREDENTIALS = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
GS_ATTENDANCE_PLAYER_MAPPING = json.loads(os.getenv('GS_ATTENDANCE_PLAYER_MAPPING')) \
    if os.getenv('GS_ATTENDANCE_PLAYER_MAPPING') else {}
GS_FAILURE_THRESHOLD = int(os.getenv('GS_FAILURE_THRESHOLD', 300))
GS_RECOVERY_TIMEOUT = int(os.getenv('GS_RECOVERY_TIMEOUT', 300))  # defaults to 5 minutes

# ----------------------------------------
# -------------- APP Metadata
# ----------------------------------------
APP_VERSION = version.__version__
