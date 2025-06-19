import logging
import sys
import pururu.config as config

_APP_LOGGER_NAME = "pururu"

_initialized = False

def setup_logging():
    global _initialized
    if _initialized:
        return

    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(AppVersionFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(config.LOG_LEVEL)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    for name in list(logging.root.manager.loggerDict):
        if not name.startswith(_APP_LOGGER_NAME):
            logging.getLogger(name).setLevel(config.THIRD_PARTY_DEFAULT_LOG_LEVEL)

    _initialized = True


class AppVersionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'extra'):
            record.extra = {}
        record.extra["app_version"] = config.APP_VERSION
        return True

def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)