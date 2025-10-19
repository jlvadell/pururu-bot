import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional

from pururu.__version__ import get_version
from pururu.common import utils
from pururu.config import settings

_APP_LOGGER_NAME = "pururu"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar('span_id', default=None)

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        trace_id = trace_id_var.get()
        span_id = span_id_var.get()
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "source": record.name,
            "message": record.getMessage(),
            "app_version": get_version(),
            "trace_id": trace_id,
            "span_id": span_id,
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


def generate_trace_id() -> str:
    """Generate a new trace ID (hex format, compatible with OpenTelemetry)"""
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """Generate a new span ID (hex format, compatible with OpenTelemetry)"""
    return uuid.uuid4().hex[:16]  # 16 character hex


def set_trace_context(trace_id: str, span_id: Optional[str] = None):
    """
    Set the trace context for the current execution context

    Args:
        trace_id: The trace ID (usually from incoming request or generated)
        span_id: Optional span ID (generated if not provided)
    """
    trace_id_var.set(trace_id)
    if span_id:
        span_id_var.set(span_id)
    else:
        span_id_var.set(generate_span_id())
