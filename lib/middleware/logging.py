import json
import logging
import time
from typing import Callable

from fastapi import Request, Response

# Standard LogRecord attributes — exclude these from JSON extra fields.
_LOGRECORD_ATTRS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime",
    "taskName",  # Python 3.12+
})

_http_logger = logging.getLogger("flex.http")


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line.

    Standard fields: ts, level, logger, msg.
    Extra fields (passed via extra={}) are merged in automatically.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k not in _LOGRECORD_ATTRS and not k.startswith("_"):
                payload[k] = v
        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Replace root logger handlers with a single JSON-to-stderr handler."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


async def log_requests(request: Request, call_next: Callable) -> Response:
    """FastAPI middleware: log every HTTP request as a JSON line."""
    start = time.monotonic()
    response = await call_next(request)
    ms = round((time.monotonic() - start) * 1000, 1)
    _http_logger.info(
        "%s %s %d",
        request.method,
        request.url.path,
        response.status_code,
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "status": response.status_code,
            "ms": ms,
        },
    )
    return response
