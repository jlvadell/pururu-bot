from datetime import datetime

import pururu.config as config

FORMATTED_TIME_STR = '%Y-%m-%d %H:%M:%S'


def get_banner() -> str:
    """
    Returns the banner for the application
    :return: str
    """
    return f"""
888888ba                                                        dP                  dP   
 88    `8b                                                       88                  88   
a88aaaa8P' dP    dP 88d888b. dP    dP 88d888b. dP    dP          88d888b. .d8888b. d8888P 
 88        88    88 88'  `88 88    88 88'  `88 88    88 88888888 88'  `88 88'  `88   88   
 88        88.  .88 88       88.  .88 88       88.  .88          88.  .88 88.  .88   88   
 dP        `88888P' dP       `88888P' dP       `88888P'          88Y8888' `88888P'   dP   
oooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo
                Pururu Bot - Version {config.APP_VERSION}
"""

def get_current_time_formatted() -> str:
    """
    Returns the current time in a formatted string, e.g. 2021-09-01 12:00:00
    :return: str
    """
    return datetime.now().strftime(FORMATTED_TIME_STR)


def format_time(time: datetime) -> str:
    """
    Formats a datetime object into a string
    :param time: datetime
    :return: str
    """
    return time.strftime(FORMATTED_TIME_STR)


def parse_time(time: str) -> datetime:
    """
    Parses a string into a datetime object
    :param time: str
    :return: datetime
    """
    return datetime.strptime(time, FORMATTED_TIME_STR)
