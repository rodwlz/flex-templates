"""Shared HTTP session for all Http*Adapter instances.

Owns the httpx.Client, JWT token (RAM only), HTTPS guard, and user cache.
Pass _client in tests to bypass network and URL validation.
"""
from __future__ import annotations

from urllib.parse import urlparse

import httpx

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})


class _HttpSession:
    def __init__(self, base_url: str, _client: httpx.Client | None = None):
        if _client is not None:
            self._client = _client
        else:
            self._validate_url(base_url)
            self._client = httpx.Client(base_url=base_url, timeout=10.0)
        self._token: str | None = None
        self._user: dict | None = None

    def _validate_url(self, base_url: str) -> None:
        parsed = urlparse(base_url)
        is_local = parsed.hostname in _LOCAL_HOSTS
        if not is_local and parsed.scheme == "http":
            raise ValueError(
                f"HTTPS required for non-localhost URL: {base_url!r}. "
                "Use https:// or connect to localhost."
            )

    def set_credentials(self, token: str, user: dict) -> None:
        self._token = token
        self._user = user

    def clear_credentials(self) -> None:
        self._token = None
        self._user = None

    def has_token(self) -> bool:
        return self._token is not None

    def get_cached_user(self) -> dict | None:
        return self._user

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return self._client.request(method, path, headers=headers, **kwargs)
