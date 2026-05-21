# Phase 5C — HttpBackendAdapter

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `HttpBackendAdapter` — an `IBackendAdapter` implementation that talks to the FastAPI layer over HTTP instead of calling Python services directly. Swap one line in `main.py` to switch from in-process to remote.

**Architecture:** Symmetric with Phase 5B. A shared `_HttpSession` helper owns the `httpx.Client`, JWT token (in-memory only), HTTPS guard, and a cached current-user dict. Four `Http*Adapter` classes implement the four `I*Adapter` interfaces. `HttpBackendAdapter` constructs and coordinates them. The FastAPI HTTP endpoints are the universal cross-language contract — any JS dashboard, mobile app, or CLI can call the same endpoints. FastAPI auto-generates `/openapi.json` for clients that want to codegen a typed SDK.

**Tech Stack:** `httpx` (sync client), existing FastAPI + JWT layer, Python ABCs — no new dependencies beyond moving `httpx` from `[dev]` to main deps.

---

## The Problem

`ServiceBackendAdapter` wires Flet views directly to Python services. This means:
- The Flet app and the backend **must run in the same process** — no remote backend, no multi-app deployments
- Other projects (JS dashboard, card game, mobile app) cannot reuse the same backend logic
- Testing the full HTTP contract requires running the whole app, not just the adapter layer

`HttpBackendAdapter` solves this by making the HTTP API the runtime interface, not just a secondary exposure.

---

## Design

### `_HttpSession` helper (`lib/adapters/http_session.py`)

Single object shared by all four `Http*Adapter` instances. Owns:
- `httpx.Client` (one connection pool for the whole adapter tree)
- `_token: str | None` — JWT, in-memory only, never written to disk, never logged
- `_user: dict | None` — cached current-user dict; populated on login, cleared on logout; eliminates chatty `/auth/me` calls
- HTTPS validation at construction time

```python
from __future__ import annotations

from urllib.parse import urlparse

import httpx

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})


class _HttpSession:
    """Shared HTTP state for all Http*Adapter instances.

    Owns the httpx.Client, JWT token (RAM-only), and the HTTPS guard.
    Pass _client directly in tests to bypass network and URL validation.
    """

    def __init__(self, base_url: str, _client: httpx.Client | None = None):
        if _client is not None:
            self._client = _client
        else:
            self._validate_url(base_url)
            self._client = httpx.Client(base_url=base_url, timeout=10.0)
        self._token: str | None = None
        self._user: dict | None = None

    # ── HTTPS guard ──────────────────────────────────────────────────────────

    def _validate_url(self, base_url: str) -> None:
        parsed = urlparse(base_url)
        is_local = parsed.hostname in _LOCAL_HOSTS
        if not is_local and parsed.scheme == "http":
            raise ValueError(
                f"HTTPS required for non-localhost URL: {base_url!r}. "
                "Use https:// or connect to localhost."
            )

    # ── Token + user cache ───────────────────────────────────────────────────

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

    # ── Request ──────────────────────────────────────────────────────────────

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Execute request, injecting Bearer token if present. Never logs token."""
        headers = kwargs.pop("headers", {})
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return self._client.request(method, path, headers=headers, **kwargs)
```

### `HttpAuthAdapter` (`lib/adapters/http_auth_adapter.py`)

```python
from __future__ import annotations

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
        resp.raise_for_status()
        body = resp.json()
        token = body["access_token"]
        # Fetch user dict and cache both together — avoids future /me call
        user_resp = self._session._client.request(
            "GET", "/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        user_resp.raise_for_status()
        user = user_resp.json()
        self._session.set_credentials(token, user)
        return {"user": user}

    def logout(self) -> None:
        self._session.clear_credentials()

    def current_user(self) -> dict | None:
        cached = self._session.get_cached_user()
        if cached is not None:
            return cached
        if not self._session.has_token():
            return None
        resp = self._session.request("GET", "/v1/auth/me")
        if resp.status_code != 200:
            return None
        user = resp.json()
        return user
```

### `HttpUserAdapter` (`lib/adapters/http_users_adapter.py`)

Converts `page/page_size` (adapter contract) ↔ `skip/limit` (API convention) and rebuilds the paginate shape from the API response.

```python
from __future__ import annotations

from lib.adapters.users_adapter import IUserAdapter
from lib.adapters.http_session import _HttpSession


class HttpUserAdapter(IUserAdapter):
    def __init__(self, session: _HttpSession):
        self._session = session

    def list(self, page: int = 1, page_size: int = 20) -> dict:
        skip = (page - 1) * page_size
        resp = self._session.request(
            "GET", "/v1/users/",
            params={"skip": skip, "limit": page_size},
        )
        resp.raise_for_status()
        body = resp.json()
        total = body.get("total", len(body["users"]))
        pages = max(1, (total + page_size - 1) // page_size)
        return {
            "items": body["users"],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    def create(self, data: dict) -> dict:
        resp = self._session.request("POST", "/v1/users/", json=data)
        resp.raise_for_status()
        return resp.json()

    def delete(self, user_id: str) -> bool:
        resp = self._session.request("DELETE", f"/v1/users/{user_id}")
        return resp.status_code == 200
```

### `HttpRoleAdapter` (`lib/adapters/http_roles_adapter.py`)

```python
from __future__ import annotations

from lib.adapters.roles_adapter import IRoleAdapter
from lib.adapters.http_session import _HttpSession


class HttpRoleAdapter(IRoleAdapter):
    def __init__(self, session: _HttpSession):
        self._session = session

    def list(self) -> list[dict]:
        resp = self._session.request("GET", "/v1/roles/")
        resp.raise_for_status()
        return resp.json()

    def create(self, name: str) -> dict:
        resp = self._session.request("POST", "/v1/roles/", json={"name": name})
        resp.raise_for_status()
        return resp.json()

    def delete(self, role_id: str) -> bool:
        resp = self._session.request("DELETE", f"/v1/roles/{role_id}")
        return resp.status_code == 200

    def assign(self, user_id: str, role_id: str) -> bool:
        resp = self._session.request(
            "POST", "/v1/roles/assign",
            json={"user_id": user_id, "role_id": role_id},
        )
        return resp.status_code == 200

    def remove(self, user_id: str, role_id: str) -> bool:
        resp = self._session.request(
            "DELETE", "/v1/roles/remove",
            json={"user_id": user_id, "role_id": role_id},
        )
        return resp.status_code == 200
```

### `HttpSchedulerAdapter` (`lib/adapters/http_scheduler_adapter.py`)

```python
from __future__ import annotations

from lib.adapters.scheduler_adapter import ISchedulerAdapter
from lib.adapters.http_session import _HttpSession


class HttpSchedulerAdapter(ISchedulerAdapter):
    def __init__(self, session: _HttpSession):
        self._session = session

    def list(self) -> list[dict]:
        resp = self._session.request("GET", "/v1/scheduler/jobs")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return resp.json()
```

### `HttpBackendAdapter` coordinator (`lib/adapters/http_backend_adapter.py`)

```python
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
    """HTTP-backed IBackendAdapter. Swap for ServiceBackendAdapter in main.py.

    base_url examples:
        "http://localhost:8080"     — local dev (HTTP allowed)
        "https://api.example.com"  — remote (HTTPS required)

    _client is a test escape hatch; pass httpx.Client(app=fastapi_app) to
    test against the FastAPI app without a real server.
    """

    def __init__(self, base_url: str, _client: httpx.Client | None = None):
        session = _HttpSession(base_url, _client)
        self._auth      = HttpAuthAdapter(session)
        self._users     = HttpUserAdapter(session)
        self._roles     = HttpRoleAdapter(session)
        self._scheduler = HttpSchedulerAdapter(session)

    @property
    def auth(self) -> IAuthAdapter:
        return self._auth

    @property
    def users(self) -> IUserAdapter:
        return self._users

    @property
    def roles(self) -> IRoleAdapter:
        return self._roles

    @property
    def scheduler(self) -> ISchedulerAdapter:
        return self._scheduler
```

### Swap in `main.py` (one line)

```python
# Current (in-process):
backend = ServiceBackendAdapter(factory, user_service, scheduler)

# HTTP (local or remote):
backend = HttpBackendAdapter(base_url="http://localhost:8080")
# backend = HttpBackendAdapter(base_url="https://api.example.com")
```

---

## New and Updated API Endpoints

All routes get the `/v1` prefix. This is the universal contract for all clients — Python, JS, mobile, CLI.

### `GET /v1/auth/me` (new — `lib/api/routes/auth.py`)

Returns the authenticated user's profile. Requires valid Bearer JWT.

```python
from lib.auth.jwt_handler import decode_token

@router.get("/me")
def me(token: str = Depends(oauth2_scheme), service: UserService = Depends(_get_service)):
    payload = decode_token(token)  # raises HTTPException 401 on invalid
    user_id = payload["sub"]
    user = service.get_user(user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user   # {id, username, email, roles} — no password_hash
```

### `POST /v1/roles/assign` (new — `lib/api/routes/roles.py`)

```python
class RoleAssignment(BaseModel):
    user_id: str
    role_id: str

@router.post("/assign")
def assign_role(body: RoleAssignment, repo: UserRepository = Depends(get_repo)):
    import uuid
    result = repo.add_role(uuid.UUID(body.user_id), uuid.UUID(body.role_id))
    if not result:
        raise HTTPException(404, "User or role not found")
    return {"assigned": True}
```

### `DELETE /v1/roles/remove` (new — `lib/api/routes/roles.py`)

```python
@router.delete("/remove")
def remove_role(body: RoleAssignment, repo: UserRepository = Depends(get_repo)):
    import uuid
    result = repo.remove_role(uuid.UUID(body.user_id), uuid.UUID(body.role_id))
    if not result:
        raise HTTPException(404, "Assignment not found")
    return {"removed": True}
```

### `GET /v1/scheduler/jobs` (new file — `lib/api/routes/scheduler.py`)

```python
from fastapi import APIRouter
from lib.database.session import ConnectionRegistry

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

_scheduler = None  # set by main.py after startup

def set_scheduler(s) -> None:
    global _scheduler
    _scheduler = s

@router.get("/jobs")
def list_jobs():
    if _scheduler is None:
        return []
    jobs = _scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "name": job.name,
            "trigger": str(job.trigger),
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
            "func_name": getattr(job.func, "__name__", str(job.func)),
        }
        for job in jobs
    ]
```

### Updated `GET /v1/users/` — add `total` (`lib/api/routes/users.py`)

Add `total` to the response so `HttpUserAdapter.list()` can compute pagination metadata:

```python
@router.get("/")
def list_users(skip: int = 0, limit: int = 20, repo: UserRepository = Depends(get_repo)):
    users = repo.list()       # or paginated query
    return {"users": users[skip:skip+limit], "total": len(users)}
```

### Route prefix change

All existing routes in `auth.py`, `users.py`, `roles.py` get `prefix="/v1/..."`:

```python
# auth.py
router = APIRouter(prefix="/v1/auth", tags=["auth"])

# users.py
router = APIRouter(prefix="/v1/users", tags=["users"])

# roles.py
router = APIRouter(prefix="/v1/roles", tags=["roles"])
```

---

## Security

### HTTPS enforcement

Validated once in `_HttpSession.__init__()` — fail fast at adapter construction time, not at first request:

```
base_url = "https://api.example.com"  → OK
base_url = "http://localhost:8080"    → OK (local)
base_url = "http://api.example.com"  → ValueError at construction
```

### JWT token lifecycle

| Event | Action |
|---|---|
| Login success | `set_credentials(token, user)` — both stored in RAM |
| Logout | `clear_credentials()` — both wiped |
| App restart | Token gone — user must log in again |
| `current_user()` called | Returns `_user` from RAM (no network call in common path) |
| request() | Adds `Authorization: Bearer {token}` header — never logged, never stored elsewhere |

**Rules enforced by design:**
- `_token` and `_user` only exist in `_HttpSession._token` and `_HttpSession._user` — no copies
- `request()` builds the Authorization header inline — the token string never passes through a logging layer
- `clear_credentials()` sets both to `None` — no references remain

---

## Testing

`Http*Adapter` tests inject the FastAPI app via the `_client` escape hatch — no real server, no new dependencies beyond `httpx` (already present):

```python
# tests/conftest.py additions

import httpx
from starlette.testclient import TestClient

@pytest.fixture
def http_backend(db_factory, user_service):
    from lib.api.app import create_app   # existing test helper or main app factory
    app = create_app(db_factory, user_service)
    raw_client = TestClient(app)
    client = httpx.Client(
        transport=httpx.WSGITransport(app=raw_client.app),
        base_url="http://test",
    )
    return HttpBackendAdapter(base_url="http://test", _client=client)
```

### `tests/test_http_adapters.py` — 18 tests

```
# Auth
test_http_login_returns_user_dict
test_http_login_bad_credentials_raises
test_http_current_user_none_before_login
test_http_current_user_after_login_uses_cache      ← no /me call if cache warm
test_http_logout_clears_user

# Users
test_http_users_list_returns_paginate_shape
test_http_users_list_page_2_offset_correct
test_http_users_create_returns_dict_with_id
test_http_users_delete_returns_true
test_http_users_delete_nonexistent_returns_false

# Roles
test_http_roles_list
test_http_roles_create
test_http_roles_delete
test_http_roles_assign
test_http_roles_remove

# Scheduler
test_http_scheduler_list_empty

# Security / HTTPS guard
test_http_https_guard_rejects_remote_http
test_http_https_guard_allows_localhost_http
test_http_https_guard_allows_https
test_http_token_not_sent_before_login
```

---

## Cross-Language Contract Note

The FastAPI endpoints added in this phase are the **universal interface** for all future projects:

- **Python Flet app (local):** `ServiceBackendAdapter` — no HTTP at all
- **Python Flet app (remote):** `HttpBackendAdapter` — uses these endpoints
- **JS dashboard:** calls `/v1/*` directly with `fetch()` or a codegen'd SDK from `/openapi.json`
- **Mobile app:** same endpoints, any HTTP client
- **CLI tools / automation:** `curl`, `httpx`, `requests`

When you add a new entity (e.g., orders), you create `IOrderAdapter` + `ServiceOrderAdapter` + `HttpOrderAdapter` and add `POST/GET/DELETE /v1/orders/*` endpoints. No existing adapter or view changes.

---

## Files

| File | Action | Notes |
|---|---|---|
| `lib/adapters/http_session.py` | Create | `_HttpSession` — HTTPS guard, token + user cache |
| `lib/adapters/http_auth_adapter.py` | Create | `HttpAuthAdapter(IAuthAdapter)` |
| `lib/adapters/http_users_adapter.py` | Create | `HttpUserAdapter(IUserAdapter)` — page↔skip conversion |
| `lib/adapters/http_roles_adapter.py` | Create | `HttpRoleAdapter(IRoleAdapter)` |
| `lib/adapters/http_scheduler_adapter.py` | Create | `HttpSchedulerAdapter(ISchedulerAdapter)` |
| `lib/adapters/http_backend_adapter.py` | Create | `HttpBackendAdapter(IBackendAdapter)` coordinator |
| `lib/api/routes/auth.py` | Modify | Add `/v1` prefix; add `GET /v1/auth/me` |
| `lib/api/routes/users.py` | Modify | Add `/v1` prefix; add `total` to list response |
| `lib/api/routes/roles.py` | Modify | Add `/v1` prefix; add `POST /v1/roles/assign`, `DELETE /v1/roles/remove` |
| `lib/api/routes/scheduler.py` | Create | `GET /v1/scheduler/jobs` |
| `pyproject.toml` | Modify | Move `httpx` from `[dev]` to main deps |
| `tests/test_http_adapters.py` | Create | 20 tests against FastAPI test client |
| `tests/test_smoke.py` | Modify | 6 new module imports |

---

## Build Order

1. Add `/v1` prefix to existing route files (`auth.py`, `users.py`, `roles.py`) + update `total` in users list — run existing 477 tests, all pass
2. `lib/api/routes/scheduler.py` — new route file
3. `GET /v1/auth/me` — add to auth.py
4. `POST /v1/roles/assign` + `DELETE /v1/roles/remove` — add to roles.py
5. `lib/adapters/http_session.py` — `_HttpSession`
6. `lib/adapters/http_auth_adapter.py` — `HttpAuthAdapter`
7. `lib/adapters/http_users_adapter.py` — `HttpUserAdapter`
8. `lib/adapters/http_roles_adapter.py` — `HttpRoleAdapter`
9. `lib/adapters/http_scheduler_adapter.py` — `HttpSchedulerAdapter`
10. `lib/adapters/http_backend_adapter.py` — coordinator
11. `tests/test_http_adapters.py` — all 20 tests pass
12. `pyproject.toml` — move `httpx` to main deps
13. `tests/test_smoke.py` — 6 new imports

All 477 existing tests must still pass after every step.
