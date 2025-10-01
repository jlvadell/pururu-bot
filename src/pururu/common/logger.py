import json
import logging
import sys

from pururu.__version__ import get_version
from pururu.common import utils
from pururu.config import settings

_APP_LOGGER_NAME = "pururu"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "source": record.name,
            "message": record.getMessage(),
            "app_version": get_version()
        }

        # Include all promoted fields from record (extra fields injected)
        for k, v in record.__dict__.items():
            if k not in log_record and not k.startswith("_") and not callable(v):
                log_record[k] = utils.serialize(v)

        return json.dumps(log_record)


def setup_logging():
    global _initialized
    if _initialized:
        return

    if settings.general.log_format_json:
        formatter = JSONFormatter(datefmt=_DATE_FORMAT)
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt=_DATE_FORMAT
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.general.log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    for name in logging.root.manager.loggerDict:
        if not name.startswith(_APP_LOGGER_NAME):
            logging.getLogger(name).setLevel(settings.general.third_party_default_log_level)

    _initialized = True


def reset_logging():
    global _initialized
    _initialized = False  # allow re-run of setup_logging()
    setup_logging()

def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
