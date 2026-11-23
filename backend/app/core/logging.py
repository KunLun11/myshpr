"""Logging configuration and request-scoped context.

Production emits one JSON object per line with stable keys so logs can be
searched by ``request_id`` and joined with metrics. Development keeps a
human-readable format. Passwords, tokens and request bodies are never logged.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings

_LOG_FORMAT_DEV = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

# Request-scoped values attached by middleware/dependencies. ContextVars are
# copied into every task that the request spawns, so background logging keeps
# the correlation id.
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)

# Extra attributes that may appear on a LogRecord and should be serialised.
_EXTRA_KEYS = (
    "request_id",
    "user_id",
    "route",
    "method",
    "status",
    "duration_ms",
    "event",
    "task",
    "count",
)


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter without third-party dependencies."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _EXTRA_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if "request_id" not in payload and (rid := request_id_ctx.get()):
            payload["request_id"] = rid
        if "user_id" not in payload and (uid := user_id_ctx.get()):
            payload["user_id"] = uid
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=_stringify)


def setup_logging() -> None:
    settings = get_settings()
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    if settings.ENV == "prod":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(_LOG_FORMAT_DEV))

    root.setLevel(level)
    root.addHandler(handler)

    # Keep noisy libraries quieter than the app.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
