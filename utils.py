import logging
from datetime import datetime

import config


def get_logger(name: str):
    """
    Creates a custom logger instance
    :param name: __name__ of the module
    :return: Logger
    """
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger(name)
    logger.setLevel(config.LOG_LEVEL)
    return logger


def get_current_time_formatted():
    """
    Returns the current time in a formatted string, e.g. 2021-09-01 12:00:00
    :return: str
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
