"""
RateLimiter — sliding-window rate limiter as a FastAPI dependency.

Uses Redis via CacheRegistry when available; falls back to an in-process
dict (safe for single-process / test deployments).

Usage:
    limiter = RateLimiter(limit=60, window=60)

    @router.get("/")
    def endpoint(_: None = Depends(limiter)):
        ...
"""
from __future__ import annotations

import time

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, limit: int, window: int = 60):
        self._limit = limit
        self._window = window
        self._local: dict[str, list[float]] = {}

    def __call__(self, request: Request) -> None:
        key = f"rl:{request.client.host}"
        if self._redis_available():
            self._check_redis(key)
        else:
            self._check_local(key)

    def _redis_available(self) -> bool:
        try:
            from lib.services.cache_registry import CacheRegistry
            CacheRegistry.get("redis")
            return True
        except Exception:
            return False

    def _check_redis(self, key: str) -> None:
        from lib.services.cache_registry import CacheRegistry
        r = CacheRegistry.get("redis")._r
        now = time.time()
        pipe = r.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, 0, now - self._window)
        pipe.zcard(key)
        pipe.expire(key, self._window)
        _, _, count, _ = pipe.execute()
        if count > self._limit:
            raise HTTPException(status_code=429, detail="Too many requests")

    def _check_local(self, key: str) -> None:
        now = time.time()
        timestamps = self._local.get(key, [])
        cutoff = now - self._window
        timestamps = [t for t in timestamps if t > cutoff]
        timestamps.append(now)
        self._local[key] = timestamps
        if len(timestamps) > self._limit:
            raise HTTPException(status_code=429, detail="Too many requests")
