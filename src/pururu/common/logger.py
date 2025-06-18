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