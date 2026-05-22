"""HttpBackendAdapter stub — users/roles/scheduler added in Tasks 7-9."""
from __future__ import annotations

import httpx

from lib.adapters.backend_adapter import IBackendAdapter
from lib.adapters.auth_adapter import IAuthAdapter
from lib.adapters.users_adapter import IUserAdapter
from lib.adapters.roles_adapter import IRoleAdapter
from lib.adapters.scheduler_adapter import ISchedulerAdapter
from lib.adapters.http_session import _HttpSession
from lib.adapters.http_auth_adapter import HttpAuthAdapter


class HttpBackendAdapter(IBackendAdapter):
    def __init__(self, base_url: str, _client: httpx.Client | None = None):
        self._session = _HttpSession(base_url, _client)
        self._auth = HttpAuthAdapter(self._session)

    @property
    def auth(self) -> IAuthAdapter:
        return self._auth

    @property
    def users(self) -> IUserAdapter:
        raise NotImplementedError("users — implemented in Task 7")

    @property
    def roles(self) -> IRoleAdapter:
        raise NotImplementedError("roles — implemented in Task 8")

    @property
    def scheduler(self) -> ISchedulerAdapter:
        raise NotImplementedError("scheduler — implemented in Task 9")
