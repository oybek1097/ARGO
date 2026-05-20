"""Structured JSON logging (spec section 8).

Provides :func:`get_logger`, which returns a stdlib :class:`logging.Logger`
configured with a :class:`JsonFormatter` so every emitted record is a
single-line JSON object containing a timestamp, level, logger name,
message, and any caller-supplied ``extra`` fields.
"""

from __future__ import annotations

import datetime
import json
import logging
from typing import Optional

# Attributes present on a stock LogRecord; anything beyond these is treated
# as a caller-supplied "extra" field and merged into the JSON output.
_STANDARD_RECORD_ATTRS = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "taskName", "message", "asctime",
    }
)


class JsonFormatter(logging.Formatter):
    """A :class:`logging.Formatter` that renders records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        """Return ``record`` serialised as a one-line JSON string."""
        timestamp = datetime.datetime.fromtimestamp(
            record.created, tz=datetime.timezone.utc
        ).isoformat()
        payload = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any caller-supplied extra fields.
        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS or key.startswith("_"):
                continue
            payload[key] = value
        # Include exception details when present.
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, sort_keys=True)


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Return a logger named ``name`` emitting structured JSON lines.

    The logger is configured exactly once: a single stream handler with a
    :class:`JsonFormatter` is attached. Propagation is disabled so the
    structured output is not duplicated by ancestor handlers.
    """
    logger = logging.getLogger(name)
    if not any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(level if level is not None else logging.INFO)
    return logger
