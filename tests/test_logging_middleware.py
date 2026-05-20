import json
import logging
from io import StringIO


def _capture_logger(name: str) -> tuple[logging.Logger, StringIO]:
    from lib.middleware.logging import JsonFormatter
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    log = logging.getLogger(name)
    log.handlers.clear()
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    log.propagate = False
    return log, stream


def test_json_formatter_produces_valid_json():
    log, stream = _capture_logger("test.jf1")
    log.info("hello world")
    output = stream.getvalue().strip()
    parsed = json.loads(output)
    assert parsed["msg"] == "hello world"
    assert parsed["level"] == "INFO"
    assert "ts" in parsed
    assert "logger" in parsed


def test_json_formatter_includes_extra_fields():
    log, stream = _capture_logger("test.jf2")
    log.info("http request", extra={"method": "GET", "status": 200, "ms": 12.3})
    parsed = json.loads(stream.getvalue().strip())
    assert parsed["method"] == "GET"
    assert parsed["status"] == 200
    assert parsed["ms"] == 12.3


def test_setup_logging_does_not_raise():
    from lib.middleware.logging import setup_logging
    setup_logging("WARNING")  # should not raise


def test_log_requests_middleware_calls_next():
    """Integration: middleware must call the next handler and return its response."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from lib.middleware.logging import log_requests

    fake_request = MagicMock()
    fake_request.method = "GET"
    fake_request.url.path = "/test"
    fake_response = MagicMock()
    fake_response.status_code = 200

    async def call_next(_): return fake_response

    response = asyncio.run(log_requests(fake_request, call_next))
    assert response is fake_response
