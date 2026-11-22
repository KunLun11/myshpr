"""Logging configuration.

Structured JSON logs in production, human-readable in dev. Never log
passwords, tokens or full request bodies.
"""

import logging
import sys

from app.core.config import get_settings

_LOG_FORMAT_DEV = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_JSON_FORMAT = (
    '{"time": "%(asctime)s", "level": "%(levelname)s", '
    '"logger": "%(name)s", "message": "%(message)s"}'
)


def setup_logging() -> None:
    settings = get_settings()
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    if settings.ENV == "prod":
        handler.setFormatter(logging.Formatter(_JSON_FORMAT))
    else:
        handler.setFormatter(logging.Formatter(_LOG_FORMAT_DEV))

    root.setLevel(level)
    root.addHandler(handler)

    # Keep noisy libraries quieter than the app.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
