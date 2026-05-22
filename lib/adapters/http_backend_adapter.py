"""HttpBackendAdapter — IBackendAdapter over HTTP.

Drop-in replacement for ServiceBackendAdapter. Swap one line in main.py:

    # In-process (current):
    backend = ServiceBackendAdapter(factory, user_service, scheduler)

    # HTTP (local or remote):
    backend = HttpBackendAdapter(base_url="http://localhost:8080")
    # backend = HttpBackendAdapter(base_url="https://api.example.com")

HTTPS is required for non-localhost URLs — ValueError at construction time.
JWT is stored in RAM only (_HttpSession._token), never logged or written to disk.

Pass _client (a TestClient or custom httpx.Client) to bypass URL validation
and use a test transport. Used by tests/conftest.py http_backend fixture.
"""
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
        session          = _HttpSession(base_url, _client)
        self._auth       = HttpAuthAdapter(session)
        self._users      = HttpUserAdapter(session)
        self._roles      = HttpRoleAdapter(session)
        self._scheduler  = HttpSchedulerAdapter(session)

    @property
    def auth(self) -> IAuthAdapter:           return self._auth
    @property
    def users(self) -> IUserAdapter:          return self._users
    @property
    def roles(self) -> IRoleAdapter:          return self._roles
    @property
    def scheduler(self) -> ISchedulerAdapter: return self._scheduler
