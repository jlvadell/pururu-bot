from datetime import datetime
from enum import Enum

from pururu.__version__ import get_version

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
                Pururu Bot - Version {get_version()}
"""


def serialize(value) -> any:
    """
    Recursively converts a value to a JSON-serializable format.
    Handles dicts, lists, tuples, datetime objects, and Enums.
    Falls back to str() for any non-serializable objects.
    :param value: value to convert
    :return: serializable value
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    elif isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, Enum):
        return value.value
    else:
        return str(value)


def deserialize(field_type, value) -> any:
    """
    Recursively converts a JSON-serializable value back to its original type.
    :param field_type: the expected type of the field
    :param value: serialized value
    :return: deserialized value
    """
    if value is None:
        return None
    elif field_type == datetime:
        return datetime.fromisoformat(value)
    elif hasattr(field_type, '__origin__') and field_type.__origin__ is list:
        # Handle list types
        inner_type = field_type.__args__[0] if field_type.__args__ else None
        return [deserialize(inner_type, item) for item in value]
    elif isinstance(field_type, type) and issubclass(field_type, Enum):
        return field_type(value)
    else:
        return value
