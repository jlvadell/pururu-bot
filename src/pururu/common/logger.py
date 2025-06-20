import datetime
import logging
import sys
import pururu.config as config
import json
from pururu.common import utils

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
            "app_version": config.APP_VERSION,
        }

        # Include all promoted fields from record (extra fields injected)
        for k, v in record.__dict__.items():
            if k not in log_record and not k.startswith("_") and not callable(v):
                log_record[k] = self.serialize_item(v)

        return json.dumps(log_record)

    def serialize_item(self, item):
        """ Serializes an item to a JSON-compatible format."""
        if isinstance(item, (str, int, float, bool)):
            return item
        elif isinstance(item, dict):
            return {k: self.serialize_item(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [self.serialize_item(i) for i in item]
        elif isinstance(item, datetime.datetime):
            return utils.format_time(item)
        else:
            return str(item)


def setup_logging():
    global _initialized
    if _initialized:
        return

    if config.LOG_FORMAT_JSON:
        formatter = JSONFormatter(datefmt=_DATE_FORMAT)
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt=_DATE_FORMAT
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(config.LOG_LEVEL)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    for name in list(logging.root.manager.loggerDict):
        if not name.startswith(_APP_LOGGER_NAME):
            logging.getLogger(name).setLevel(config.THIRD_PARTY_DEFAULT_LOG_LEVEL)

    _initialized = True

def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)