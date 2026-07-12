"""
Centralized logging configuration.

Every module in the app imports get_logger(__name__) instead of using
print(), so log output is consistent, filterable by level, and easy to
redirect to a file or log aggregator in production.
"""

import logging
import sys
from functools import lru_cache

from app.config.settings import settings


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON, useful for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def _build_root_handler() -> logging.Handler:
    """Create the single stdout handler shared by all loggers in the app."""
    handler = logging.StreamHandler(sys.stdout)

    if settings.log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    return handler


@lru_cache
def _configure_root_once() -> None:
    """
    Configure the root logger exactly once per process.

    lru_cache with no arguments guarantees this body runs only on the
    first call, so repeated imports never attach duplicate handlers
    (which would otherwise print every log line multiple times).
    """
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    root.addHandler(_build_root_handler())

    # ChromaDB's bundled posthog telemetry client has a known bug in some
    # versions that logs a harmless error on every operation. We silence
    # just this logger rather than suppressing errors app-wide.
    logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger for the given module name.

    Usage:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    _configure_root_once()
    return logging.getLogger(name)