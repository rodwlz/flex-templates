"""HttpBackendAdapter stub — will be finalized in Task 10."""
from __future__ import annotations

import httpx

from lib.adapters.backend_adapter import IBackendAdapter
from lib.adapters.auth_adapter import IAuthAdapter
from lib.adapters.users_adapter import IUserAdapter
from lib.adapters.roles_adapter import IRoleAdapter
from lib.adapters.scheduler_adapter import ISchedulerAdapter
from lib.adapters.http_session import _HttpSession
from lib.adapters.http_auth_adapter import HttpAuthAdapter
from lib.adapters.http_users_adapter import HttpUserAdapter
from lib.adapters.http_roles_adapter import HttpRoleAdapter
from lib.adapters.http_scheduler_adapter import HttpSchedulerAdapter


class HttpBackendAdapter(IBackendAdapter):
    def __init__(self, base_url: str, _client: httpx.Client | None = None):
        self._session    = _HttpSession(base_url, _client)
        self._auth       = HttpAuthAdapter(self._session)
        self._users      = HttpUserAdapter(self._session)
        self._roles      = HttpRoleAdapter(self._session)
        self._scheduler  = HttpSchedulerAdapter(self._session)

    @property
    def auth(self) -> IAuthAdapter:           return self._auth
    @property
    def users(self) -> IUserAdapter:          return self._users
    @property
    def roles(self) -> IRoleAdapter:          return self._roles
    @property
    def scheduler(self) -> ISchedulerAdapter: return self._scheduler
