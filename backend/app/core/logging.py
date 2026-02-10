"""Structured logging: JSON in production, human-readable in dev. All logs can include request_id."""
import json
import logging
from datetime import datetime

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON for production."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "msg": record.getMessage(),
            "logger": record.name,
        }
        # Include extra={...} fields (e.g. request_id, method, path, status_code, latency_ms)
        skip = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs", "message", "msg",
            "name", "pathname", "process", "processName", "relativeCreated",
            "stack_info", "thread", "threadName",
        }
        for k, v in getattr(record, "__dict__", {}).items():
            if k in skip:
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except (TypeError, ValueError):
                payload[k] = str(v)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str = "app") -> logging.Logger:
    """Return a logger with env-appropriate formatter (JSON in production). Idempotent."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    if settings.APP_ENV == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(levelname)s [%(name)s] %(message)s")
        )
    logger.addHandler(handler)
    logger.propagate = False
    return logger
