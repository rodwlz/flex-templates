"""HTTP implementation of IAuthAdapter."""
from __future__ import annotations

import httpx

from lib.adapters.auth_adapter import IAuthAdapter
from lib.adapters.http_session import _HttpSession


class HttpAuthAdapter(IAuthAdapter):
    def __init__(self, session: _HttpSession):
        self._session = session

    def login(self, username: str, password: str) -> dict:
        resp = self._session.request(
            "POST", "/v1/auth/login",
            data={"username": username, "password": password},
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise ValueError("Invalid credentials") from exc
            raise
        token = resp.json()["access_token"]
        # Store token so the /me request includes Authorization header
        self._session.set_credentials(token, {})
        me_resp = self._session.request("GET", "/v1/auth/me")
        me_resp.raise_for_status()
        user = me_resp.json()
        self._session.set_credentials(token, user)
        return {"user": user}

    def logout(self) -> None:
        self._session.clear_credentials()

    def current_user(self) -> dict | None:
        cached = self._session.get_cached_user()
        if cached:
            return cached
        if not self._session.has_token():
            return None
        resp = self._session.request("GET", "/v1/auth/me")
        if resp.status_code != 200:
            return None
        return resp.json()
