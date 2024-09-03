import logging
from datetime import datetime

import pururu.config as config

FORMATTED_TIME_STR = '%Y-%m-%d %H:%M:%S'


def get_logger(name: str):
    """
    Creates a custom logger instance
    :param name: __name__ of the module
    :return: Logger
    """
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt=FORMATTED_TIME_STR,
                        level=config.LOG_LEVEL,
                        force=True)
    logger = logging.getLogger(name)
    return logger


def get_current_time_formatted():
    """
    Returns the current time in a formatted string, e.g. 2021-09-01 12:00:00
    :return: str
    """
    return datetime.now().strftime(FORMATTED_TIME_STR)
