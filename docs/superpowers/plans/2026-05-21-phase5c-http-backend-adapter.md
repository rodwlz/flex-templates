# Phase 5C — HttpBackendAdapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `HttpBackendAdapter` — an `IBackendAdapter` that calls FastAPI over HTTP — so any Python Flet app, JS dashboard, or CLI can talk to the same backend by swapping one line in `main.py`.

**Architecture:** All API routes get a `/v1` prefix (universal, versioned contract). A shared `_HttpSession` helper owns the `httpx.Client`, JWT token (RAM-only), HTTPS guard, and cached user dict. Four `Http*Adapter` classes mirror the Phase 5B Service*Adapter decomposition. `HttpBackendAdapter` coordinates them identically to `ServiceBackendAdapter`. Swap is one line in `main.py`.

**Tech Stack:** `httpx` (sync), FastAPI `TestClient` for testing, Python ABCs, existing JWT/auth layer — no new runtime dependencies beyond moving `httpx` from `[dev]` to main.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `lib/api/routes/auth.py` | Modify | Add `/v1` prefix; add `GET /v1/auth/me` |
| `lib/api/routes/users.py` | Modify | Add `/v1` prefix; add `total` to list response |
| `lib/api/routes/roles.py` | Modify | Add `/v1` prefix; add assign + remove endpoints |
| `lib/api/routes/caches.py` | Modify | Add `/v1` prefix |
| `lib/api/routes/scheduler.py` | Create | `GET /v1/scheduler/jobs` |
| `lib/auth/dependencies.py` | Modify | Update `tokenUrl` to `/v1/auth/login` |
| `lib/services/user_service.py` | Modify | `list()` adds `total`, applies skip/limit |
| `lib/adapters/http_session.py` | Create | Shared HTTPS guard + JWT cache |
| `lib/adapters/http_auth_adapter.py` | Create | `HttpAuthAdapter(IAuthAdapter)` |
| `lib/adapters/http_users_adapter.py` | Create | `HttpUserAdapter(IUserAdapter)` |
| `lib/adapters/http_roles_adapter.py` | Create | `HttpRoleAdapter(IRoleAdapter)` |
| `lib/adapters/http_scheduler_adapter.py` | Create | `HttpSchedulerAdapter(ISchedulerAdapter)` |
| `lib/adapters/http_backend_adapter.py` | Create | `HttpBackendAdapter(IBackendAdapter)` coordinator |
| `pyproject.toml` | Modify | Move `httpx` from `[dev]` to main deps |
| `tests/conftest.py` | Modify | Add `http_factory`, `http_backend`, `test_user` fixtures |
| `tests/test_http_session.py` | Create | `_HttpSession` unit tests |
| `tests/test_http_adapters.py` | Create | Http*Adapter integration tests |
| `tests/test_api.py` | Modify | Update URLs `/users` → `/v1/users` |
| `tests/test_api_routes.py` | Modify | Update URLs `/users` + `/roles` → `/v1/...` |
| `tests/test_api_caches.py` | Modify | Update URLs `/caches` → `/v1/caches` |
| `tests/test_smoke.py` | Modify | Add 7 new module imports |

---

## Task 1: Add /v1 prefix to all routes, add `total` to users list, fix existing API tests

**Context:** All four existing route files get a `/v1` prefix. `UserService.list()` gains a `total` field and respects `skip`/`limit`. Existing API test URL strings are updated to match.

**Files:**
- Modify: `lib/api/routes/auth.py` (line 19)
- Modify: `lib/api/routes/users.py` (line 29)
- Modify: `lib/api/routes/roles.py` (line 15)
- Modify: `lib/api/routes/caches.py` (line 27)
- Modify: `lib/auth/dependencies.py` (line 7)
- Modify: `lib/services/user_service.py` (lines 37-49)
- Modify: `tests/test_api.py` (4 URL strings)
- Modify: `tests/test_api_routes.py` (multiple URL strings)
- Modify: `tests/test_api_caches.py` (URL strings)

- [ ] **Step 1: Update the four router prefix lines**

In `lib/api/routes/auth.py` line 19, change:
```python
router = APIRouter(prefix="/auth", tags=["auth"])
```
to:
```python
router = APIRouter(prefix="/v1/auth", tags=["auth"])
```

In `lib/api/routes/users.py` line 29, change:
```python
router = APIRouter(prefix="/users", tags=["users"])
```
to:
```python
router = APIRouter(prefix="/v1/users", tags=["users"])
```

In `lib/api/routes/roles.py` line 15, change:
```python
router = APIRouter(prefix="/roles", tags=["roles"])
```
to:
```python
router = APIRouter(prefix="/v1/roles", tags=["roles"])
```

In `lib/api/routes/caches.py` line 27, change:
```python
router = APIRouter(prefix="/caches", tags=["caches"])
```
to:
```python
router = APIRouter(prefix="/v1/caches", tags=["caches"])
```

- [ ] **Step 2: Update tokenUrl in dependencies.py**

In `lib/auth/dependencies.py` line 7, change:
```python
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
```
to:
```python
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")
```

- [ ] **Step 3: Update UserService.list() to add total + apply skip/limit**

In `lib/services/user_service.py`, replace the `list` method (lines 36-49):
```python
    def list(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        users = repo.list()
        skip = data.get("skip", 0)
        limit = data.get("limit", len(users))
        sliced = users[skip:skip + limit]
        return {
            "users": [
                {
                    "id": str(u.id),
                    "username": u.username,
                    "email": u.email,
                    "role_count": len(u.roles),
                }
                for u in sliced
            ],
            "total": len(users),
        }
```

- [ ] **Step 4: Run the existing API tests — they should all fail (wrong URLs)**

```
pytest tests/test_api.py tests/test_api_routes.py tests/test_api_caches.py -v
```
Expected: many 404s because URLs are now `/v1/users` not `/users`.

- [ ] **Step 5: Fix test_api.py URL strings**

In `tests/test_api.py`, update every URL:
- Line 72: `client.get(f"/users/{user.id}")` → `client.get(f"/v1/users/{user.id}")`
- Line 84: `client.get(f"/users/{uuid.uuid4()}")` → `client.get(f"/v1/users/{uuid.uuid4()}")`
- Line 96: `client.get("/users/not-a-uuid")` → `client.get("/v1/users/not-a-uuid")`
- Line 107: `client.get("/users")` → `client.get("/v1/users")`
- Line 116: `client.get("/users")` → `client.get("/v1/users")`

Also fix the strict equality check for empty list (line 127):
```python
# OLD:
    assert response.json() == {"users": []}

# NEW:
    body = response.json()
    assert body["users"] == []
    assert body["total"] == 0
```

- [ ] **Step 6: Fix test_api_routes.py URL strings**

In `tests/test_api_routes.py`, update every URL:
- All `/roles` → `/v1/roles` (lines 62, 75, 76, 88, 94, 95, 96, 99, 113, 114, 119, 120, 125, 128)
- All `/users` → `/v1/users` (lines 138, 155, 158, 168, 169, 170, 176, 177, 182, 187, 188, 191, 201, 204, 214, 217, 219, 228, 234, 241, 244, 252, 255)

- [ ] **Step 7: Fix test_api_caches.py URL strings**

In `tests/test_api_caches.py`, update every URL:
- All `/caches` → `/v1/caches` (lines 31, 38, 48, 56, 63, 73, 82, 94, 101, 107, 113, 120)

- [ ] **Step 8: Verify all API tests pass**

```
pytest tests/test_api.py tests/test_api_routes.py tests/test_api_caches.py -v
```
Expected: all pass.

- [ ] **Step 9: Run full suite to confirm no regressions**

```
pytest -x -q
```
Expected: 477 passing.

- [ ] **Step 10: Commit**

```bash
git add lib/api/routes/auth.py lib/api/routes/users.py lib/api/routes/roles.py lib/api/routes/caches.py lib/auth/dependencies.py lib/services/user_service.py tests/test_api.py tests/test_api_routes.py tests/test_api_caches.py
git commit -m "feat: add /v1 prefix to all API routes; add total to users list"
```

---

## Task 2: GET /v1/scheduler/jobs

**Context:** New route file for scheduler jobs. Uses a module-level `_scheduler = None`; returns `[]` when no scheduler is set (test-safe). `main.py` calls `set_scheduler()` after startup.

**Files:**
- Create: `lib/api/routes/scheduler.py`

- [ ] **Step 1: Create the route file**

Create `lib/api/routes/scheduler.py`:
```python
"""GET /v1/scheduler/jobs — list running APScheduler jobs."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1/scheduler", tags=["scheduler"])

_scheduler = None


def set_scheduler(scheduler) -> None:
    """Called from main.py after scheduler.start()."""
    global _scheduler
    _scheduler = scheduler


@router.get("/jobs")
def list_jobs() -> list[dict]:
    """Return all scheduled jobs. Returns [] if no scheduler is running."""
    if _scheduler is None:
        return []
    return [
        {
            "id": job.id,
            "name": job.name,
            "trigger": str(job.trigger),
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
            "func_name": getattr(job.func, "__name__", str(job.func)),
        }
        for job in _scheduler.get_jobs()
    ]
```

- [ ] **Step 2: Verify import works**

```
pytest tests/test_smoke.py::test_module_imports_cleanly -k "scheduler" -v
```
Expected: SKIP (module not in smoke list yet — added in Task 12).

Run quick import check:
```
python -c "from lib.api.routes import scheduler; print('OK')"
```
Expected: `OK`.

- [ ] **Step 3: Run full suite**

```
pytest -x -q
```
Expected: 477 passing.

- [ ] **Step 4: Commit**

```bash
git add lib/api/routes/scheduler.py
git commit -m "feat: add GET /v1/scheduler/jobs route"
```

---

## Task 3: GET /v1/auth/me

**Context:** Returns the authenticated user's full profile. Reuses the existing `get_current_user` dependency (validates Bearer JWT, returns `{id, roles}`) then fetches full user data via `UserService.get()`.

**Files:**
- Modify: `lib/api/routes/auth.py`

- [ ] **Step 1: Add the /me endpoint to auth.py**

The full updated `lib/api/routes/auth.py`:
```python
"""
Authentication endpoints — OAuth2 password flow.

POST /v1/auth/login  accepts application/x-www-form-urlencoded (OAuth2PasswordRequestForm).
GET  /v1/auth/me     returns the authenticated user's profile (requires Bearer JWT).
"""
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from lib.auth.dependencies import get_current_user
from lib.auth.jwt_handler import create_token
from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.user_service import UserService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _get_service() -> UserService:
    return UserService(ConnectionRegistry.get())


@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(_get_service),
):
    """Authenticate with username/email + password (OAuth2 password flow). Returns Bearer JWT."""
    result = service.execute(ActionRequest(
        action="authenticate",
        data={"username": form.username, "password": form.password},
    ))
    if not result.success:
        time.sleep(0.5)
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_token({"sub": result.data["id"], "roles": result.data["roles"]})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(
    current: dict = Depends(get_current_user),
    service: UserService = Depends(_get_service),
):
    """Return the authenticated user's full profile (id, username, email, roles)."""
    result = service.execute(ActionRequest(action="get", data={"id": current["id"]}))
    if not result.success:
        raise HTTPException(status_code=404, detail="User not found")
    return result.data
```

- [ ] **Step 2: Write a quick integration smoke test**

Create `tests/test_auth_me.py`:
```python
"""Integration test for GET /v1/auth/me."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.api.routes import auth as auth_routes
from lib.api.routes import users as users_routes
from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.services.user_service import UserService


def _mem_factory():
    factory = SessionFactory.__new__(SessionFactory)
    factory._engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory._Session = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=factory._engine
    )
    return factory


@pytest.fixture
def auth_client(monkeypatch):
    factory = _mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    svc = UserService(factory)
    svc.create_user(username="alice", email="alice@example.com", password="pass123")
    app = FastAPI()
    app.include_router(auth_routes.router)
    app.include_router(users_routes.router)
    return TestClient(app)


def test_me_returns_user_profile(auth_client):
    login = auth_client.post(
        "/v1/auth/login",
        data={"username": "alice", "password": "pass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = auth_client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert "password_hash" not in body


def test_me_returns_401_without_token(auth_client):
    response = auth_client.get("/v1/auth/me")
    assert response.status_code == 401
```

- [ ] **Step 3: Run the test — expect it to fail**

```
pytest tests/test_auth_me.py -v
```
Expected: FAIL (endpoint doesn't exist yet — we just created it in Step 1, so if it already passes, great).

- [ ] **Step 4: Run the test**

```
pytest tests/test_auth_me.py -v
```
Expected: both tests PASS.

- [ ] **Step 5: Run full suite**

```
pytest -x -q
```
Expected: 479 passing.

- [ ] **Step 6: Commit**

```bash
git add lib/api/routes/auth.py tests/test_auth_me.py
git commit -m "feat: add GET /v1/auth/me endpoint"
```

---

## Task 4: POST /v1/roles/assign + DELETE /v1/roles/remove

**Context:** Two new endpoints that assign and remove roles from users. They go through `UserRepository.add_role()` / `UserRepository.remove_role()` directly — these already exist and return `bool`.

**Files:**
- Modify: `lib/api/routes/roles.py`

- [ ] **Step 1: Write failing tests for the new endpoints**

Create `tests/test_api_roles_assign.py`:
```python
"""Integration tests for POST /v1/roles/assign and DELETE /v1/roles/remove."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.api.routes import roles as roles_routes
from lib.api.routes import users as users_routes
from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.services.user_service import UserService
from lib.services.role_service import RoleService


def _mem_factory():
    factory = SessionFactory.__new__(SessionFactory)
    factory._engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory._Session = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=factory._engine
    )
    return factory


@pytest.fixture
def assign_client(monkeypatch):
    factory = _mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    app = FastAPI()
    app.include_router(roles_routes.router)
    app.include_router(users_routes.router)
    return TestClient(app), factory


def test_assign_role_returns_200(assign_client):
    client, factory = assign_client
    user = UserService(factory).create_user("bob", "bob@x.com", "pass")
    role = RoleService(factory).create_role("admin")

    resp = client.post("/v1/roles/assign", json={
        "user_id": user["id"], "role_id": role["id"]
    })
    assert resp.status_code == 200
    assert resp.json()["assigned"] is True


def test_assign_role_404_on_bad_ids(assign_client):
    client, _ = assign_client
    import uuid
    resp = client.post("/v1/roles/assign", json={
        "user_id": str(uuid.uuid4()), "role_id": str(uuid.uuid4())
    })
    assert resp.status_code == 404


def test_remove_role_returns_200(assign_client):
    client, factory = assign_client
    user = UserService(factory).create_user("carol", "carol@x.com", "pass")
    role = RoleService(factory).create_role("editor")

    client.post("/v1/roles/assign", json={
        "user_id": user["id"], "role_id": role["id"]
    })
    resp = client.delete("/v1/roles/remove", json={
        "user_id": user["id"], "role_id": role["id"]
    })
    assert resp.status_code == 200
    assert resp.json()["removed"] is True


def test_remove_role_404_when_not_assigned(assign_client):
    client, factory = assign_client
    user = UserService(factory).create_user("dave", "dave@x.com", "pass")
    role = RoleService(factory).create_role("viewer")

    resp = client.delete("/v1/roles/remove", json={
        "user_id": user["id"], "role_id": role["id"]
    })
    assert resp.status_code == 404
```

- [ ] **Step 2: Run the tests — expect failures (endpoints don't exist yet)**

```
pytest tests/test_api_roles_assign.py -v
```
Expected: 404 errors on POST /v1/roles/assign and DELETE /v1/roles/remove.

- [ ] **Step 3: Add assign and remove endpoints to roles.py**

The complete updated `lib/api/routes/roles.py`:
```python
"""
REST endpoints for the Role resource.

Uses RoleService (SimpleService) for CRUD. assign/remove go through
UserRepository directly because they are user↔role relationship ops.
Role.id is uuid.UUID — FastAPI parses it from the URL automatically.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.repositories.user_repository import UserRepository
from lib.services.role_service import RoleService

router = APIRouter(prefix="/v1/roles", tags=["roles"])


def get_service() -> RoleService:
    return RoleService(ConnectionRegistry.get())


class _RoleAssignment(BaseModel):
    user_id: str
    role_id: str


@router.post("")
def create_role(data: dict, service: RoleService = Depends(get_service)):
    """Create a new role."""
    result = service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.get("")
def list_roles(service: RoleService = Depends(get_service)):
    """List all roles."""
    result = service.execute(ActionRequest(action="list", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.get("/{role_id}")
def get_role(role_id: str, service: RoleService = Depends(get_service)):
    """Get a role by ID."""
    result = service.execute(ActionRequest(action="get", data={"id": role_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data


@router.delete("/{role_id}")
def delete_role(role_id: str, service: RoleService = Depends(get_service)):
    """Delete a role."""
    result = service.execute(ActionRequest(action="delete", data={"id": role_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data


@router.post("/assign")
def assign_role(body: _RoleAssignment):
    """Assign a role to a user."""
    repo = UserRepository(ConnectionRegistry.get())
    result = repo.add_role(uuid.UUID(body.user_id), uuid.UUID(body.role_id))
    if not result:
        raise HTTPException(404, detail="User or role not found")
    return {"assigned": True}


@router.delete("/remove")
def remove_role(body: _RoleAssignment):
    """Remove a role from a user."""
    repo = UserRepository(ConnectionRegistry.get())
    result = repo.remove_role(uuid.UUID(body.user_id), uuid.UUID(body.role_id))
    if not result:
        raise HTTPException(404, detail="Assignment not found")
    return {"removed": True}
```

**Note:** `/assign` and `/remove` must be declared BEFORE `/{role_id}` to avoid FastAPI treating "assign" as a role ID. The ordering above is correct.

- [ ] **Step 4: Run the new tests**

```
pytest tests/test_api_roles_assign.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Run full suite**

```
pytest -x -q
```
Expected: 483 passing.

- [ ] **Step 6: Commit**

```bash
git add lib/api/routes/roles.py tests/test_api_roles_assign.py
git commit -m "feat: add POST /v1/roles/assign and DELETE /v1/roles/remove"
```

---

## Task 5: _HttpSession

**Context:** The shared helper that all Http*Adapter instances hold a reference to. Owns the httpx.Client, JWT token (RAM-only), HTTPS enforcement, and cached user dict. Unit-tested in isolation using a `MagicMock` client.

**Files:**
- Create: `lib/adapters/http_session.py`
- Create: `tests/test_http_session.py`

- [ ] **Step 1: Write failing tests for _HttpSession**

Create `tests/test_http_session.py`:
```python
"""Unit tests for _HttpSession — HTTPS guard, token lifecycle, header injection."""
from unittest.mock import MagicMock, call

import httpx
import pytest

from lib.adapters.http_session import _HttpSession


def _mock_session() -> _HttpSession:
    """Return a session with a MagicMock client (no real network)."""
    return _HttpSession("http://ignored", _client=MagicMock(spec=httpx.Client))


# ── HTTPS guard ───────────────────────────────────────────────────────────────

def test_https_guard_rejects_remote_http():
    with pytest.raises(ValueError, match="HTTPS required"):
        _HttpSession("http://api.example.com")


def test_https_guard_allows_localhost_http():
    # httpx.Client(base_url="http://localhost:8080") doesn't fail at construction.
    session = _HttpSession("http://localhost:8080")
    assert session.has_token() is False  # constructed successfully


def test_https_guard_allows_127_http():
    session = _HttpSession("http://127.0.0.1:8080")
    assert session.has_token() is False


def test_https_guard_allows_https_remote():
    session = _HttpSession("https://api.example.com")
    assert session.has_token() is False


# ── Token + user cache ────────────────────────────────────────────────────────

def test_no_auth_header_before_credentials_set():
    session = _mock_session()
    session.request("GET", "/test")
    _, kwargs = session._client.request.call_args
    assert "Authorization" not in kwargs.get("headers", {})


def test_auth_header_after_set_credentials():
    session = _mock_session()
    session.set_credentials("tok123", {"id": "u1"})
    session.request("GET", "/test")
    _, kwargs = session._client.request.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer tok123"


def test_clear_credentials_removes_token_and_user():
    session = _mock_session()
    session.set_credentials("tok123", {"id": "u1"})
    session.clear_credentials()
    assert session.has_token() is False
    assert session.get_cached_user() is None


def test_no_auth_header_after_clear():
    session = _mock_session()
    session.set_credentials("tok123", {"id": "u1"})
    session.clear_credentials()
    session.request("GET", "/test")
    _, kwargs = session._client.request.call_args
    assert "Authorization" not in kwargs.get("headers", {})


def test_get_cached_user_returns_none_initially():
    session = _mock_session()
    assert session.get_cached_user() is None


def test_get_cached_user_returns_stored_dict():
    session = _mock_session()
    session.set_credentials("tok", {"id": "u1", "username": "alice"})
    assert session.get_cached_user() == {"id": "u1", "username": "alice"}
```

- [ ] **Step 2: Run the tests — expect ImportError (module doesn't exist yet)**

```
pytest tests/test_http_session.py -v
```
Expected: ImportError — `lib.adapters.http_session` not found.

- [ ] **Step 3: Implement _HttpSession**

Create `lib/adapters/http_session.py`:
```python
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
```

- [ ] **Step 4: Run the tests**

```
pytest tests/test_http_session.py -v
```
Expected: all 10 tests PASS.

- [ ] **Step 5: Run full suite**

```
pytest -x -q
```
Expected: 493 passing.

- [ ] **Step 6: Commit**

```bash
git add lib/adapters/http_session.py tests/test_http_session.py
git commit -m "feat: add _HttpSession — HTTPS guard and JWT token cache"
```

---

## Task 6: HttpAuthAdapter + shared test fixtures

**Context:** First Http*Adapter. Add shared fixtures to `conftest.py` that all Http adapter tests use. Tests go in `tests/test_http_adapters.py`. The fixture wires a FastAPI app (with all v1 routes) to an `HttpBackendAdapter` via a `TestClient`.

**Files:**
- Modify: `tests/conftest.py`
- Create: `tests/test_http_adapters.py`
- Create: `lib/adapters/http_auth_adapter.py`

- [ ] **Step 1: Add shared fixtures to tests/conftest.py**

Add the following to the bottom of `tests/conftest.py`:
```python
# ── HTTP adapter test infrastructure ─────────────────────────────────────────

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def _http_mem_factory() -> SessionFactory:
    """In-memory SQLite that keeps one connection alive (for HTTP adapter tests)."""
    factory = SessionFactory.__new__(SessionFactory)
    factory._engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory._Session = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=factory._engine
    )
    return factory


@pytest.fixture
def http_factory(monkeypatch):
    """In-memory DB registered as 'postgres' — shared by http_backend + test_user."""
    factory = _http_mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(
        ConnectionRegistry,
        "_factories",
        {"postgres": factory},
    )
    return factory


@pytest.fixture
def http_app(http_factory):
    """FastAPI app with all v1 routes — used by http_backend fixture."""
    from fastapi import FastAPI
    from lib.api.routes import (
        auth as auth_routes,
        users as users_routes,
        roles as roles_routes,
        scheduler as scheduler_routes,
    )
    app = FastAPI()
    app.include_router(auth_routes.router)
    app.include_router(users_routes.router)
    app.include_router(roles_routes.router)
    app.include_router(scheduler_routes.router)
    return app


@pytest.fixture
def http_backend(http_app):
    """HttpBackendAdapter wired to the in-memory test FastAPI app.

    Import is deferred so this fixture only fails if the Http adapter files
    are actually missing — not on every test run before Phase 5C is built.
    """
    from fastapi.testclient import TestClient
    from lib.adapters.http_backend_adapter import HttpBackendAdapter
    client = TestClient(http_app)
    return HttpBackendAdapter(base_url="http://testserver", _client=client)


@pytest.fixture
def test_user(http_factory):
    """Create a real user in the test DB; returns {username, password, email}."""
    from lib.services.user_service import UserService
    svc = UserService(http_factory)
    svc.create_user(username="testuser", email="test@example.com", password="testpass123")
    return {"username": "testuser", "password": "testpass123", "email": "test@example.com"}
```

Also add the missing imports at the top of conftest.py (after existing imports):
```python
from lib.database.session import ConnectionRegistry  # already imported? check line 29
```
(If `ConnectionRegistry` isn't already imported, add it to the existing import line.)

- [ ] **Step 2: Write failing tests for HttpAuthAdapter**

Create `tests/test_http_adapters.py`:
```python
"""Integration tests for Http*Adapters against a real FastAPI test app."""
import pytest


# ── Auth ─────────────────────────────────────────────────────────────────────

def test_http_login_returns_user_dict(http_backend, test_user):
    result = http_backend.auth.login(test_user["username"], test_user["password"])
    assert "user" in result
    assert result["user"]["username"] == test_user["username"]
    assert result["user"]["email"] == test_user["email"]
    assert "password_hash" not in result["user"]


def test_http_login_bad_credentials_raises(http_backend):
    with pytest.raises(ValueError):
        http_backend.auth.login("nobody", "wrongpass")


def test_http_current_user_none_before_login(http_backend):
    assert http_backend.auth.current_user() is None


def test_http_current_user_after_login(http_backend, test_user):
    http_backend.auth.login(test_user["username"], test_user["password"])
    user = http_backend.auth.current_user()
    assert user is not None
    assert user["username"] == test_user["username"]


def test_http_current_user_uses_cache(http_backend, test_user):
    """Two consecutive calls return identical dicts (cache, not two /me requests)."""
    http_backend.auth.login(test_user["username"], test_user["password"])
    u1 = http_backend.auth.current_user()
    u2 = http_backend.auth.current_user()
    assert u1 == u2


def test_http_logout_clears_user(http_backend, test_user):
    http_backend.auth.login(test_user["username"], test_user["password"])
    http_backend.auth.logout()
    assert http_backend.auth.current_user() is None
```

- [ ] **Step 3: Run the tests — expect ImportError**

```
pytest tests/test_http_adapters.py -v
```
Expected: ImportError — `lib.adapters.http_backend_adapter` not found (in conftest fixture).

- [ ] **Step 4: Implement HttpAuthAdapter**

Create `lib/adapters/http_auth_adapter.py`:
```python
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
        # Store token so the /me request includes it
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
        user = resp.json()
        return user
```

**Note:** `http_backend` fixture depends on `HttpBackendAdapter` which doesn't exist yet. Create a stub for now so the fixture doesn't crash:

Create `lib/adapters/http_backend_adapter.py` (stub — will be completed in Task 10):
```python
"""HttpBackendAdapter stub — replaced in Task 10."""
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
```

- [ ] **Step 5: Run only auth tests**

```
pytest tests/test_http_adapters.py -k "auth or login or logout or current_user" -v
```
Expected: all 6 auth tests PASS.

- [ ] **Step 6: Run full suite**

```
pytest -x -q
```
Expected: 499 passing (6 new auth tests + 10 from session tests already passing).

- [ ] **Step 7: Commit**

```bash
git add lib/adapters/http_auth_adapter.py lib/adapters/http_backend_adapter.py tests/test_http_adapters.py tests/conftest.py
git commit -m "feat: add HttpAuthAdapter and shared http test fixtures"
```

---

## Task 7: HttpUserAdapter

**Context:** Converts `page/page_size` (adapter contract) ↔ `skip/limit` (API query params) and rebuilds the paginate shape from the API response.

**Files:**
- Create: `lib/adapters/http_users_adapter.py`
- Modify: `lib/adapters/http_backend_adapter.py` (wire in HttpUserAdapter)
- Modify: `tests/test_http_adapters.py` (add user tests)

- [ ] **Step 1: Add failing user tests to tests/test_http_adapters.py**

Append to `tests/test_http_adapters.py`:
```python
# ── Users ─────────────────────────────────────────────────────────────────────

def test_http_users_list_returns_paginate_shape(http_backend, test_user):
    result = http_backend.users.list()
    assert "items" in result
    assert "total" in result
    assert "page" in result
    assert "page_size" in result
    assert "pages" in result
    assert result["total"] >= 1


def test_http_users_list_page2_offset(http_backend, http_factory):
    """Page 2 with page_size=1 returns the second user."""
    from lib.services.user_service import UserService
    svc = UserService(http_factory)
    svc.create_user("user_a", "a@x.com", "pass")
    svc.create_user("user_b", "b@x.com", "pass")
    result = http_backend.users.list(page=2, page_size=1)
    assert result["page"] == 2
    assert len(result["items"]) == 1


def test_http_users_create_returns_dict_with_id(http_backend):
    result = http_backend.users.create({
        "username": "newuser", "email": "new@x.com", "password": "pass",
    })
    assert "id" in result
    assert result["username"] == "newuser"


def test_http_users_delete_returns_true(http_backend, http_factory):
    from lib.services.user_service import UserService
    user = UserService(http_factory).create_user("todelete", "del@x.com", "pass")
    result = http_backend.users.delete(user["id"])
    assert result is True


def test_http_users_delete_nonexistent_returns_false(http_backend):
    import uuid
    result = http_backend.users.delete(str(uuid.uuid4()))
    assert result is False
```

- [ ] **Step 2: Run only user tests — expect failures**

```
pytest tests/test_http_adapters.py -k "users" -v
```
Expected: `NotImplementedError` from stub.

- [ ] **Step 3: Implement HttpUserAdapter**

Create `lib/adapters/http_users_adapter.py`:
```python
"""HTTP implementation of IUserAdapter."""
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
        users = body.get("users", [])
        total = body.get("total", len(users))
        pages = max(1, (total + page_size - 1) // page_size)
        return {
            "items": users,
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

- [ ] **Step 4: Wire HttpUserAdapter into the stub HttpBackendAdapter**

In `lib/adapters/http_backend_adapter.py`, update the stub:
```python
"""HttpBackendAdapter stub — roles and scheduler added in Tasks 8-9."""
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


class HttpBackendAdapter(IBackendAdapter):
    def __init__(self, base_url: str, _client: httpx.Client | None = None):
        self._session = _HttpSession(base_url, _client)
        self._auth  = HttpAuthAdapter(self._session)
        self._users = HttpUserAdapter(self._session)

    @property
    def auth(self) -> IAuthAdapter:
        return self._auth

    @property
    def users(self) -> IUserAdapter:
        return self._users

    @property
    def roles(self) -> IRoleAdapter:
        raise NotImplementedError("roles — implemented in Task 8")

    @property
    def scheduler(self) -> ISchedulerAdapter:
        raise NotImplementedError("scheduler — implemented in Task 9")
```

- [ ] **Step 5: Run user tests**

```
pytest tests/test_http_adapters.py -k "users" -v
```
Expected: all 5 user tests PASS.

- [ ] **Step 6: Run full suite**

```
pytest -x -q
```
Expected: 504 passing.

- [ ] **Step 7: Commit**

```bash
git add lib/adapters/http_users_adapter.py lib/adapters/http_backend_adapter.py tests/test_http_adapters.py
git commit -m "feat: add HttpUserAdapter"
```

---

## Task 8: HttpRoleAdapter

**Files:**
- Create: `lib/adapters/http_roles_adapter.py`
- Modify: `lib/adapters/http_backend_adapter.py`
- Modify: `tests/test_http_adapters.py`

- [ ] **Step 1: Add failing role tests to tests/test_http_adapters.py**

Append to `tests/test_http_adapters.py`:
```python
# ── Roles ─────────────────────────────────────────────────────────────────────

def test_http_roles_list_empty(http_backend):
    result = http_backend.roles.list()
    assert result == []


def test_http_roles_create(http_backend):
    role = http_backend.roles.create("admin")
    assert "id" in role
    assert role["name"] == "admin"


def test_http_roles_delete(http_backend):
    role = http_backend.roles.create("viewer")
    result = http_backend.roles.delete(role["id"])
    assert result is True


def test_http_roles_assign(http_backend, test_user):
    role = http_backend.roles.create("editor")
    http_backend.auth.login(test_user["username"], test_user["password"])
    user = http_backend.auth.current_user()
    result = http_backend.roles.assign(user["id"], role["id"])
    assert result is True


def test_http_roles_remove(http_backend, test_user):
    role = http_backend.roles.create("moderator")
    http_backend.auth.login(test_user["username"], test_user["password"])
    user = http_backend.auth.current_user()
    http_backend.roles.assign(user["id"], role["id"])
    result = http_backend.roles.remove(user["id"], role["id"])
    assert result is True
```

- [ ] **Step 2: Run only role tests — expect failures**

```
pytest tests/test_http_adapters.py -k "roles" -v
```
Expected: `NotImplementedError` from stub.

- [ ] **Step 3: Implement HttpRoleAdapter**

Create `lib/adapters/http_roles_adapter.py`:
```python
"""HTTP implementation of IRoleAdapter."""
from __future__ import annotations

from lib.adapters.roles_adapter import IRoleAdapter
from lib.adapters.http_session import _HttpSession


class HttpRoleAdapter(IRoleAdapter):
    def __init__(self, session: _HttpSession):
        self._session = session

    def list(self) -> list[dict]:
        resp = self._session.request("GET", "/v1/roles/")
        resp.raise_for_status()
        return resp.json().get("roles", [])

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

- [ ] **Step 4: Wire HttpRoleAdapter into stub HttpBackendAdapter**

In `lib/adapters/http_backend_adapter.py`:
```python
"""HttpBackendAdapter stub — scheduler added in Task 9."""
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


class HttpBackendAdapter(IBackendAdapter):
    def __init__(self, base_url: str, _client: httpx.Client | None = None):
        self._session    = _HttpSession(base_url, _client)
        self._auth       = HttpAuthAdapter(self._session)
        self._users      = HttpUserAdapter(self._session)
        self._roles      = HttpRoleAdapter(self._session)

    @property
    def auth(self) -> IAuthAdapter:      return self._auth
    @property
    def users(self) -> IUserAdapter:     return self._users
    @property
    def roles(self) -> IRoleAdapter:     return self._roles

    @property
    def scheduler(self) -> ISchedulerAdapter:
        raise NotImplementedError("scheduler — implemented in Task 9")
```

- [ ] **Step 5: Run role tests**

```
pytest tests/test_http_adapters.py -k "roles" -v
```
Expected: all 5 role tests PASS.

- [ ] **Step 6: Run full suite**

```
pytest -x -q
```
Expected: 509 passing.

- [ ] **Step 7: Commit**

```bash
git add lib/adapters/http_roles_adapter.py lib/adapters/http_backend_adapter.py tests/test_http_adapters.py
git commit -m "feat: add HttpRoleAdapter"
```

---

## Task 9: HttpSchedulerAdapter

**Files:**
- Create: `lib/adapters/http_scheduler_adapter.py`
- Modify: `lib/adapters/http_backend_adapter.py`
- Modify: `tests/test_http_adapters.py`

- [ ] **Step 1: Add failing scheduler test to tests/test_http_adapters.py**

Append to `tests/test_http_adapters.py`:
```python
# ── Scheduler ─────────────────────────────────────────────────────────────────

def test_http_scheduler_list_empty(http_backend):
    """Scheduler route returns [] when no scheduler is running."""
    result = http_backend.scheduler.list()
    assert result == []
```

- [ ] **Step 2: Run the test — expect NotImplementedError**

```
pytest tests/test_http_adapters.py -k "scheduler" -v
```
Expected: `NotImplementedError`.

- [ ] **Step 3: Implement HttpSchedulerAdapter**

Create `lib/adapters/http_scheduler_adapter.py`:
```python
"""HTTP implementation of ISchedulerAdapter."""
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

- [ ] **Step 4: Wire HttpSchedulerAdapter into the stub HttpBackendAdapter**

In `lib/adapters/http_backend_adapter.py`:
```python
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
```

- [ ] **Step 5: Run scheduler test**

```
pytest tests/test_http_adapters.py -k "scheduler" -v
```
Expected: PASS.

- [ ] **Step 6: Run full suite**

```
pytest -x -q
```
Expected: 510 passing.

- [ ] **Step 7: Commit**

```bash
git add lib/adapters/http_scheduler_adapter.py lib/adapters/http_backend_adapter.py tests/test_http_adapters.py
git commit -m "feat: add HttpSchedulerAdapter"
```

---

## Task 10: Finalize HttpBackendAdapter coordinator

**Context:** The stub already has all four adapters wired in (progressively built in Tasks 6-9). This task adds the docstring, adds `IBackendAdapter` conformance check (satisfies the abstract property contract), and writes an end-to-end test that exercises all four domains in sequence.

**Files:**
- Modify: `lib/adapters/http_backend_adapter.py` (finalize docstring, clean stub comments)
- Modify: `tests/test_http_adapters.py` (add end-to-end test)

- [ ] **Step 1: Add end-to-end test**

Append to `tests/test_http_adapters.py`:
```python
# ── End-to-end: HttpBackendAdapter satisfies IBackendAdapter ──────────────────

def test_http_backend_adapter_end_to_end(http_backend, test_user, http_factory):
    """All four domains work in sequence through HttpBackendAdapter."""
    from lib.adapters.backend_adapter import IBackendAdapter
    assert isinstance(http_backend, IBackendAdapter)

    # auth
    http_backend.auth.login(test_user["username"], test_user["password"])
    user = http_backend.auth.current_user()
    assert user["username"] == test_user["username"]

    # users
    listing = http_backend.users.list()
    assert listing["total"] >= 1

    # roles
    role = http_backend.roles.create("superuser")
    http_backend.roles.assign(user["id"], role["id"])
    http_backend.roles.remove(user["id"], role["id"])
    http_backend.roles.delete(role["id"])

    # scheduler
    jobs = http_backend.scheduler.list()
    assert isinstance(jobs, list)

    # logout
    http_backend.auth.logout()
    assert http_backend.auth.current_user() is None
```

- [ ] **Step 2: Run the end-to-end test**

```
pytest tests/test_http_adapters.py -k "end_to_end" -v
```
Expected: PASS.

- [ ] **Step 3: Finalize the HttpBackendAdapter docstring**

Replace `lib/adapters/http_backend_adapter.py` with the final version:
```python
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
```

- [ ] **Step 4: Run all Http adapter tests**

```
pytest tests/test_http_adapters.py tests/test_http_session.py -v
```
Expected: all pass.

- [ ] **Step 5: Run full suite**

```
pytest -x -q
```
Expected: 511 passing.

- [ ] **Step 6: Commit**

```bash
git add lib/adapters/http_backend_adapter.py tests/test_http_adapters.py
git commit -m "feat: finalize HttpBackendAdapter coordinator"
```

---

## Task 11: Move httpx to main dependencies

**Context:** `httpx` was in `[dev]` extras. Now that `HttpBackendAdapter` is a runtime class, it must be a main dependency.

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Move httpx from [dev] to main dependencies**

In `pyproject.toml`, move `"httpx>=0.27"` from `[project.optional-dependencies] dev` into `[project.dependencies]`.

The updated `dependencies` list:
```toml
dependencies = [
    "flet>=0.84",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "cryptography>=42.0",
    "sqlalchemy>=2.0",
    "alembic>=1.12",
    "redis>=5.0",
    "pandas>=2.0",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "bcrypt>=4.0",
    "python-jose[cryptography]>=3.3",
    "python-multipart>=0.0.12",
    "apscheduler>=3.10",
    "httpx>=0.27",
]
```

The updated `[dev]` extras (httpx removed):
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "fakeredis>=2.20",
    "anyio[trio]>=4.0",
]
```

- [ ] **Step 2: Verify tests still run**

```
pytest -x -q
```
Expected: 511 passing (no change — httpx was already installed).

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: move httpx from dev to main dependencies"
```

---

## Task 12: Update smoke tests

**Context:** Add the seven new modules to the smoke-test import list so any future breakage is caught immediately.

**Files:**
- Modify: `tests/test_smoke.py`

- [ ] **Step 1: Add new module paths to the parametrize list**

In `tests/test_smoke.py`, add these entries to the `@pytest.mark.parametrize` list (after the existing `lib.adapters.scheduler_adapter` entry):
```python
        "lib.adapters.http_session",
        "lib.adapters.http_auth_adapter",
        "lib.adapters.http_users_adapter",
        "lib.adapters.http_roles_adapter",
        "lib.adapters.http_scheduler_adapter",
        "lib.adapters.http_backend_adapter",
        "lib.api.routes.scheduler",
```

- [ ] **Step 2: Run the smoke tests**

```
pytest tests/test_smoke.py -v
```
Expected: all pass including the 7 new import tests.

- [ ] **Step 3: Run the full suite**

```
pytest -q
```
Expected: 518 passing (511 + 7 new smoke import tests).

- [ ] **Step 4: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: add Phase 5C modules to smoke import tests"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|---|---|
| `_HttpSession` — HTTPS guard | Task 5 |
| `_HttpSession` — token RAM-only, never logged | Task 5 (design) + `http_session.py` |
| `_HttpSession` — cached user dict | Task 5 |
| `HttpAuthAdapter` — login/logout/current_user | Task 6 |
| `HttpUserAdapter` — list/create/delete, page↔skip | Task 7 |
| `HttpRoleAdapter` — list/create/delete/assign/remove | Task 8 |
| `HttpSchedulerAdapter` — list | Task 9 |
| `HttpBackendAdapter` coordinator | Task 10 |
| `GET /v1/auth/me` | Task 3 |
| `POST /v1/roles/assign`, `DELETE /v1/roles/remove` | Task 4 |
| `GET /v1/scheduler/jobs` | Task 2 |
| `/v1` prefix on all routes | Task 1 |
| `total` in users list | Task 1 |
| `httpx` to main deps | Task 11 |
| Smoke tests | Task 12 |
| HTTPS guard tests | Task 5 |
| Token not sent before login | Task 5 |
| 18+ HTTP adapter tests | Tasks 6-10 |

**No placeholders found.**

**Type consistency:** `IAuthAdapter`, `IUserAdapter`, `IRoleAdapter`, `ISchedulerAdapter` interface names consistent throughout. `_HttpSession` method names (`set_credentials`, `clear_credentials`, `has_token`, `get_cached_user`, `request`) used consistently in Tasks 5-10.
