"""Unit tests for RateLimiter — in-memory fallback only (no Redis required)."""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from lib.api.rate_limiter import RateLimiter


def _req(host: str = "127.0.0.1") -> MagicMock:
    req = MagicMock()
    req.client.host = host
    return req


def test_allows_requests_under_limit():
    """Requests up to the limit succeed without raising."""
    limiter = RateLimiter(limit=3, window=60)
    req = _req()
    for _ in range(3):
        limiter(req)  # no exception


def test_raises_429_when_limit_exceeded():
    """The request immediately after the limit raises HTTP 429."""
    limiter = RateLimiter(limit=3, window=60)
    req = _req()
    for _ in range(3):
        limiter(req)
    with pytest.raises(HTTPException) as exc:
        limiter(req)
    assert exc.value.status_code == 429
    assert exc.value.detail == "Too many requests"


def test_tracks_clients_independently():
    """Filling one client's bucket does not affect a different client."""
    limiter = RateLimiter(limit=2, window=60)
    for _ in range(2):
        limiter(_req("10.0.0.1"))
    limiter(_req("10.0.0.2"))  # different client — no exception


def test_expired_timestamps_are_evicted():
    """Timestamps older than window are discarded; bucket refills after window."""
    import time
    limiter = RateLimiter(limit=2, window=1)  # 1-second window
    req = _req()
    for _ in range(2):
        limiter(req)
    time.sleep(1.05)
    limiter(req)  # window expired — no exception
