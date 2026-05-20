# Phase 4 Views Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a swappable `BackendAdapter` layer, a `ProtectedView` auth guard, and four new/upgraded Flet views (Login, Manage Users, Manage Roles, Scheduler admin) that never import services directly.

**Architecture:** `IBackendAdapter` is the plug between every Flet view and the backend. `ServiceBackendAdapter` is today's concrete implementation — calls services/repos directly, no HTTP. Swap it for `HttpBackendAdapter` in `main.py` alone and all views continue working unchanged. `ProtectedView(BaseView)` redirects unauthenticated users to `/login` before `build_content()` runs. The vault starts locked; `SecurityView` emits `vault.unlocked` after the user unlocks, which triggers connection registration in `main.py`.

**Tech Stack:** Flet 0.84+, SQLAlchemy 2.0, APScheduler 3.x, pydantic-settings, existing FlexTemplates contracts and fixtures

**Spec:** `docs/superpowers/specs/2026-05-20-views-phase4-design.md`

---

## File Map

| File | Action | Notes |
|---|---|---|
| `lib/adapters/backend_adapter.py` | Create | `IBackendAdapter` ABC + `ServiceBackendAdapter` |
| `lib/tasks/scheduler.py` | Modify | Add `get_jobs()` public method |
| `lib/ui/layouts/protected_view.py` | Create | Auth guard base class |
| `lib/ui/components/manage_tabs.py` | Create | Pill bar for /manage/ section |
| `lib/views/manage/__init__.py` | Create | Empty package marker |
| `lib/views/manage/users.py` | Create | Paginated user list + create + delete |
| `lib/views/manage/roles.py` | Create | Role list + create + delete |
| `lib/views/admin/scheduler.py` | Create | Read-only job inspector |
| `lib/views/login.py` | Modify | Upgrade stub to real auth |
| `lib/views/security.py` | Modify | Subclass ProtectedView + emit vault.unlocked |
| `lib/views/admin/databases.py` | Modify | Subclass ProtectedView |
| `lib/views/admin/caches.py` | Modify | Subclass ProtectedView |
| `lib/ui/layouts/base_view.py` | Modify | Add Manage to SIDEBAR_ITEMS |
| `lib/ui/components/admin_tabs.py` | Modify | Add Scheduler pill |
| `main.py` | Modify | Remove vault.unlock(), add vault.unlocked handler, wire adapter into props, register 3 routes |
| `tests/conftest.py` | Modify | Add `overlay = []` to FakePage |
| `tests/test_backend_adapter.py` | Create | Adapter unit tests |
| `tests/test_protected_view.py` | Create | Auth guard tests |
| `tests/test_smoke.py` | Modify | Add new module imports |

---

### Task 1: TaskScheduler.get_jobs() + BackendAdapter + tests

**Files:**
- Modify: `lib/tasks/scheduler.py`
- Create: `lib/adapters/backend_adapter.py`
- Create: `tests/test_backend_adapter.py`

- [ ] **Step 1: Add `get_jobs()` to TaskScheduler**

Open `lib/tasks/scheduler.py`. The file currently ends after `stop()`. Add one method:

```python
def get_jobs(self) -> list:
    """Return all APScheduler Job objects (read-only inspector)."""
    return self._scheduler.get_jobs()
```

Full file after change:
```python
"""Background task scheduler powered by APScheduler."""
from apscheduler.schedulers.background import BackgroundScheduler


class TaskScheduler:
    """Thin wrapper around APScheduler for background jobs.

    Wire into main.py start/stop lifecycle:
        scheduler = TaskScheduler()
        scheduler.add_job(my_func, "interval", hours=24)
        scheduler.start()   # before ft.run() / _stop.wait()
        # ... app runs ...
        scheduler.stop()    # in finally block

    Trigger types (APScheduler):
        "interval"  — recurring on fixed interval (seconds=, minutes=, hours=)
        "cron"      — cron-style scheduling (hour=9, minute=0, day_of_week="mon-fri")
        "date"      — run once at a specific datetime
    """

    def __init__(self):
        self._scheduler = BackgroundScheduler()

    def add_job(self, func, trigger: str = "interval", **kwargs):
        """Schedule *func* with *trigger* and APScheduler kwargs."""
        return self._scheduler.add_job(func, trigger, **kwargs)

    def get_jobs(self) -> list:
        """Return all APScheduler Job objects (read-only inspector)."""
        return self._scheduler.get_jobs()

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
```

- [ ] **Step 2: Write failing tests for BackendAdapter**

Create `tests/test_backend_adapter.py`:

```python
"""Unit tests for ServiceBackendAdapter."""
import uuid
import pytest

from lib.adapters.backend_adapter import ServiceBackendAdapter
from lib.services.user_service import UserService
from lib.repositories.role_repository import RoleRepository
from lib.tasks.scheduler import TaskScheduler


@pytest.fixture
def adapter(db_factory):
    user_service = UserService(db_factory)
    role_repo = RoleRepository(db_factory)
    scheduler = TaskScheduler()
    return ServiceBackendAdapter(db_factory, user_service, role_repo, scheduler)


@pytest.fixture
def adapter_with_user(adapter):
    adapter.create_user({"username": "alice", "email": "alice@test.com", "password": "secret"})
    return adapter


def test_login_stores_session(adapter_with_user):
    result = adapter_with_user.login("alice", "secret")
    assert result["user"]["username"] == "alice"
    assert adapter_with_user.current_user()["username"] == "alice"


def test_logout_clears_session(adapter_with_user):
    adapter_with_user.login("alice", "secret")
    adapter_with_user.logout()
    assert adapter_with_user.current_user() is None


def test_current_user_none_before_login(adapter):
    assert adapter.current_user() is None


def test_login_raises_on_bad_credentials(adapter_with_user):
    with pytest.raises(ValueError):
        adapter_with_user.login("alice", "wrong")


def test_list_users_returns_paginate_shape(adapter_with_user):
    result = adapter_with_user.list_users(page=1, page_size=10)
    assert "items" in result
    assert "total" in result
    assert "pages" in result
    assert result["page"] == 1
    assert result["total"] >= 1


def test_create_user_returns_dict_with_id(adapter):
    user = adapter.create_user({"username": "bob", "email": "bob@test.com", "password": "pw"})
    assert user["username"] == "bob"
    assert "id" in user


def test_delete_user_returns_true(adapter):
    user = adapter.create_user({"username": "carol", "email": "carol@test.com", "password": "pw"})
    assert adapter.delete_user(user["id"]) is True


def test_delete_nonexistent_user_returns_false(adapter):
    assert adapter.delete_user(str(uuid.uuid4())) is False


def test_list_roles_empty_initially(adapter):
    assert adapter.list_roles() == []


def test_create_role_returns_dict(adapter):
    role = adapter.create_role("admin")
    assert role["name"] == "admin"
    assert "id" in role


def test_delete_role_returns_true(adapter):
    role = adapter.create_role("mod")
    assert adapter.delete_role(role["id"]) is True


def test_list_roles_after_create(adapter):
    adapter.create_role("viewer")
    roles = adapter.list_roles()
    assert any(r["name"] == "viewer" for r in roles)


def test_assign_and_remove_role(adapter):
    user = adapter.create_user({"username": "dave", "email": "dave@t.com", "password": "pw"})
    role = adapter.create_role("editor")
    assert adapter.assign_role(user["id"], role["id"]) is True
    assert adapter.remove_role(user["id"], role["id"]) is True


def test_list_jobs_empty_without_scheduled_jobs(adapter):
    assert adapter.list_jobs() == []


def test_list_jobs_returns_registered_job(adapter):
    scheduler = TaskScheduler()
    from lib.services.user_service import UserService
    from lib.repositories.role_repository import RoleRepository
    import pytest
    svc = UserService(adapter._factory)
    rr = RoleRepository(adapter._factory)
    a2 = ServiceBackendAdapter(adapter._factory, svc, rr, scheduler)
    scheduler.add_job(lambda: None, "interval", seconds=3600, id="test-job", name="test job")
    scheduler.start()
    jobs = a2.list_jobs()
    assert any(j["id"] == "test-job" for j in jobs)
    scheduler.stop()
```

- [ ] **Step 3: Run tests — expect ImportError (module doesn't exist yet)**

```
pytest tests/test_backend_adapter.py -v
```

Expected: `ModuleNotFoundError: No module named 'lib.adapters.backend_adapter'`

- [ ] **Step 4: Create `lib/adapters/backend_adapter.py`**

```python
"""Backend adapter layer — decouples Flet views from services/HTTP.

Today: ServiceBackendAdapter calls services directly (no network hop).
Tomorrow: swap for HttpBackendAdapter in main.py — zero view changes.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from lib.database.session import SessionFactory
from lib.repositories.role_repository import RoleRepository
from lib.repositories.user_repository import UserRepository
from lib.services.user_service import UserService


class IBackendAdapter(ABC):

    # ── Auth ──────────────────────────────────────────────────────────────
    @abstractmethod
    def login(self, username: str, password: str) -> dict:
        """Returns {"user": {id, username, email, roles}} on success.
        Raises ValueError on bad credentials."""

    @abstractmethod
    def logout(self) -> None: ...

    @abstractmethod
    def current_user(self) -> dict | None:
        """Returns logged-in user dict or None if not authenticated."""

    # ── Users ─────────────────────────────────────────────────────────────
    @abstractmethod
    def list_users(self, page: int = 1, page_size: int = 20, **filters) -> dict:
        """Returns paginate() shape: {items, total, page, page_size, pages}.
        Items are dicts with string UUIDs."""

    @abstractmethod
    def create_user(self, data: dict) -> dict: ...

    @abstractmethod
    def delete_user(self, user_id: str) -> bool: ...

    # ── Roles ─────────────────────────────────────────────────────────────
    @abstractmethod
    def list_roles(self) -> list[dict]: ...

    @abstractmethod
    def create_role(self, name: str) -> dict: ...

    @abstractmethod
    def delete_role(self, role_id: str) -> bool: ...

    @abstractmethod
    def assign_role(self, user_id: str, role_id: str) -> bool: ...

    @abstractmethod
    def remove_role(self, user_id: str, role_id: str) -> bool: ...

    # ── Scheduler ─────────────────────────────────────────────────────────
    @abstractmethod
    def list_jobs(self) -> list[dict]:
        """Returns [{id, name, trigger, next_run_time, func_name}, ...]"""


class ServiceBackendAdapter(IBackendAdapter):
    """Concrete adapter: calls Python services/repos directly.

    Swap for HttpBackendAdapter in main.py — views are unaffected.
    """

    def __init__(self, factory: SessionFactory, user_service: UserService, scheduler):
        self._factory = factory
        self._user_service = user_service
        self._scheduler = scheduler
        self._session: dict | None = None

    # ── Auth ──────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> dict:
        user = self._user_service.authenticate_user(username, password)
        self._session = user
        return {"user": user}

    def logout(self) -> None:
        self._session = None

    def current_user(self) -> dict | None:
        return self._session

    # ── Users ─────────────────────────────────────────────────────────────

    def list_users(self, page: int = 1, page_size: int = 20, **filters) -> dict:
        repo = UserRepository(self._factory)
        result = repo.paginate(page=page, page_size=page_size)
        result["items"] = [_str_uuids(item) for item in result["items"]]
        return result

    def create_user(self, data: dict) -> dict:
        return self._user_service.create_user(
            username=data["username"],
            email=data["email"],
            password=data.get("password", ""),
        )

    def delete_user(self, user_id: str) -> bool:
        return self._user_service.delete_user(user_id)

    # ── Roles ─────────────────────────────────────────────────────────────

    def list_roles(self) -> list[dict]:
        repo = RoleRepository(self._factory)
        return [_str_uuids(r) for r in repo.filter_by()]

    def create_role(self, name: str) -> dict:
        repo = RoleRepository(self._factory)
        role = repo.create({"name": name})
        return {"id": str(role.id), "name": role.name}

    def delete_role(self, role_id: str) -> bool:
        repo = RoleRepository(self._factory)
        return repo.delete(uuid.UUID(role_id))

    def assign_role(self, user_id: str, role_id: str) -> bool:
        repo = UserRepository(self._factory)
        return repo.add_role(uuid.UUID(user_id), uuid.UUID(role_id))

    def remove_role(self, user_id: str, role_id: str) -> bool:
        repo = UserRepository(self._factory)
        return repo.remove_role(uuid.UUID(user_id), uuid.UUID(role_id))

    # ── Scheduler ─────────────────────────────────────────────────────────

    def list_jobs(self) -> list[dict]:
        jobs = self._scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": str(job.next_run_time) if job.next_run_time else "—",
                "func_name": getattr(job.func, "__name__", str(job.func)),
            }
            for job in jobs
        ]


def _str_uuids(d: dict) -> dict:
    """Stringify any uuid.UUID values in *d* so views get plain strings."""
    return {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in d.items()}
```

- [ ] **Step 5: Run tests — all pass**

```
pytest tests/test_backend_adapter.py -v
```

Expected: all 16 tests pass.

- [ ] **Step 6: Run full suite — no regressions**

```
pytest tests/ -v --tb=short -q
```

Expected: all previously passing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add lib/adapters/backend_adapter.py lib/tasks/scheduler.py tests/test_backend_adapter.py
git commit -m "feat: BackendAdapter layer + TaskScheduler.get_jobs()"
```

---

### Task 2: ProtectedView

**Files:**
- Create: `lib/ui/layouts/protected_view.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_protected_view.py`

- [ ] **Step 1: Add `overlay` to FakePage in conftest.py**

Open `tests/conftest.py`. The `FakePage` class currently has `route`, `views`, `update_count`. Add `overlay`:

```python
class FakePage:
    """Stand-in for ft.Page. Records what would have happened without rendering."""

    def __init__(self, route: str = "/"):
        self.route = route
        self.views = []
        self.overlay = []
        self.update_count = 0

    def update(self):
        self.update_count += 1

    def go(self, url: str):
        self.route = url

    def run_task(self, coro_fn, *args, **kwargs):
        """Run async tasks synchronously so test assertions see the result."""
        import asyncio
        asyncio.run(coro_fn(*args, **kwargs))
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_protected_view.py`:

```python
"""ProtectedView — auth guard base class tests."""
import flet as ft
import pytest

from lib.ui.layouts.protected_view import ProtectedView
from tests.conftest import FakePage


class _MockBackendLoggedIn:
    def current_user(self):
        return {"id": "1", "username": "alice", "roles": []}


class _MockBackendLoggedOut:
    def current_user(self):
        return None


class _ContentView(ProtectedView):
    title = "Secret"

    def build_content(self):
        return ft.Text("secret content")


def _make(route, backend, nav_service):
    page = FakePage(route)
    props = {"nav_service": nav_service, "backend": backend}
    return _ContentView(page, props)


def test_renders_normally_when_logged_in(nav_service):
    v = _make("/secret", _MockBackendLoggedIn(), nav_service)
    result = v.render()
    assert result.appbar is not None


def test_redirects_to_login_when_logged_out(nav_service):
    v = _make("/secret", _MockBackendLoggedOut(), nav_service)
    result = v.render()
    assert result.controls == []


def test_redirect_returns_view_with_current_route(nav_service):
    v = _make("/manage/users", _MockBackendLoggedOut(), nav_service)
    result = v.render()
    assert result.route == "/manage/users"


def test_redirects_when_backend_key_missing(nav_service):
    page = FakePage("/secret")
    props = {"nav_service": nav_service}  # no "backend" key
    v = _ContentView(page, props)
    result = v.render()
    assert result.controls == []
```

- [ ] **Step 3: Run tests — expect ImportError**

```
pytest tests/test_protected_view.py -v
```

Expected: `ModuleNotFoundError: No module named 'lib.ui.layouts.protected_view'`

- [ ] **Step 4: Create `lib/ui/layouts/protected_view.py`**

```python
"""ProtectedView — auth guard.

Subclass instead of BaseView for any view that requires login.
Redirects to /login if backend.current_user() returns None.
"""
from __future__ import annotations

import flet as ft

from lib.contracts.base import ActionRequest
from lib.ui.layouts.base_view import BaseView


class ProtectedView(BaseView):
    """Base class for views requiring authentication.

    render() checks backend.current_user() before calling build_content().
    Returns an empty View (triggering a /login redirect) if not authenticated.
    """

    def render(self) -> ft.View:
        backend = self.props.get("backend")
        if not backend or not backend.current_user():
            self.nav_service.execute(
                ActionRequest(action="visit", data={"url": "/login"})
            )
            return ft.View(route=self.page.route or "/", controls=[])
        return super().render()
```

- [ ] **Step 5: Run tests — all pass**

```
pytest tests/test_protected_view.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Run full suite — no regressions**

```
pytest tests/ -v --tb=short -q
```

- [ ] **Step 7: Commit**

```bash
git add lib/ui/layouts/protected_view.py tests/test_protected_view.py tests/conftest.py
git commit -m "feat: ProtectedView auth guard + FakePage.overlay"
```

---

### Task 3: ManageTabs + navigation updates

**Files:**
- Create: `lib/ui/components/manage_tabs.py`
- Modify: `lib/ui/components/admin_tabs.py`
- Modify: `lib/ui/layouts/base_view.py`

No new tests needed — these are pure UI components tested visually and by smoke test.

- [ ] **Step 1: Create `lib/ui/components/manage_tabs.py`**

```python
"""Manage section sub-navigation — pill-style tabs for /manage/ views."""
from __future__ import annotations

import flet as ft

from lib.contracts.base import ActionRequest


MANAGE_TABS: list[tuple[str, str, str]] = [
    ("Users", "/manage/users", ft.Icons.PEOPLE),
    ("Roles", "/manage/roles", ft.Icons.VERIFIED_USER),
]


class ManageTabs(ft.Container):
    """Horizontal pill bar linking between /manage/ views.

    Highlights the tab matching *current_route*.
    """

    def __init__(self, current_route: str, nav_service):
        pills = [
            self._pill(label, route, icon, current_route, nav_service)
            for label, route, icon in MANAGE_TABS
        ]
        super().__init__(
            content=ft.Row(pills, spacing=8),
            padding=ft.padding.only(bottom=20),
        )

    @staticmethod
    def _pill(label: str, route: str, icon, current_route: str, nav_service) -> ft.Container:
        active = current_route == route
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, size=16, color=ft.Colors.WHITE if active else ft.Colors.BLUE_GREY_300),
                    ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.BOLD if active else ft.FontWeight.NORMAL,
                        color=ft.Colors.WHITE if active else ft.Colors.BLUE_GREY_300,
                    ),
                ],
                spacing=6,
                tight=True,
            ),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            bgcolor=ft.Colors.BLUE_700 if active else ft.Colors.BLUE_GREY_800,
            border_radius=20,
            on_click=None if active else (
                lambda _e, r=route: nav_service.execute(
                    ActionRequest(action="visit", data={"url": r})
                )
            ),
        )
```

- [ ] **Step 2: Add Scheduler pill to `lib/ui/components/admin_tabs.py`**

Current `ADMIN_TABS`:
```python
ADMIN_TABS: list[tuple[str, str, str]] = [
    ("Databases", "/admin/databases", ft.Icons.STORAGE),
    ("Caches",    "/admin/caches",    ft.Icons.BOLT),
]
```

Change to:
```python
ADMIN_TABS: list[tuple[str, str, str]] = [
    ("Databases", "/admin/databases", ft.Icons.STORAGE),
    ("Caches",    "/admin/caches",    ft.Icons.BOLT),
    ("Scheduler", "/admin/scheduler", ft.Icons.SCHEDULE),
]
```

- [ ] **Step 3: Add Manage to `SIDEBAR_ITEMS` in `lib/ui/layouts/base_view.py`**

Current `SIDEBAR_ITEMS`:
```python
SIDEBAR_ITEMS = [
    ("Home", "/"),
    ("Login", "/login"),
    ("Products", "/products"),
    ("Security", "/security"),
    ("Admin", "/admin/databases"),
]
```

Change to:
```python
SIDEBAR_ITEMS = [
    ("Home",     "/"),
    ("Login",    "/login"),
    ("Products", "/products"),
    ("Manage",   "/manage/users"),
    ("Security", "/security"),
    ("Admin",    "/admin/databases"),
]
```

- [ ] **Step 4: Run full suite — no regressions**

```
pytest tests/ -v --tb=short -q
```

- [ ] **Step 5: Commit**

```bash
git add lib/ui/components/manage_tabs.py lib/ui/components/admin_tabs.py lib/ui/layouts/base_view.py
git commit -m "feat: ManageTabs component + Scheduler admin tab + Manage sidebar entry"
```

---

### Task 4: main.py — vault startup + adapter + routes

**Files:**
- Modify: `main.py`
- Create: `lib/views/manage/__init__.py`

- [ ] **Step 1: Create the empty manage package**

Create `lib/views/manage/__init__.py` as an empty file (content: empty string or single newline).

- [ ] **Step 2: Read `main.py` lines 95–130 to see the vault + registry block**

The relevant section currently looks like this (lines ~99–145):

```python
vault = Vault(vault_service)
vault.unlock()

# Register databases from vault — keys named DATABASE_* hold connection URLs.
for key in vault.keys():
    if key.startswith("DATABASE_"):
        db_name = key[len("DATABASE_"):].lower()
        try:
            ConnectionRegistry.register(url=vault.get(key), name=db_name)
        except Exception as e:
            print(f"Warning: Failed to register vault database '{db_name}': {e}")

# Caches — scan vault for SERVICE_URL[_ID] keys and register each adapter.
_register_caches_from_vault(vault)
```

And later in `router.set_props_factory`:
```python
router.set_props_factory(lambda: {
    "nav":    nav,
    ...
})
```

- [ ] **Step 3: Apply the three changes to `main.py`**

**Change A — remove vault.unlock() and the inline vault DB/cache registration, replace with an event-driven handler.** Find and replace this block:

```python
vault = Vault(vault_service)
vault.unlock()

# Register databases from vault — keys named DATABASE_* hold connection URLs.
# This keeps credentials out of .env entirely.
for key in vault.keys():
    if key.startswith("DATABASE_"):
        db_name = key[len("DATABASE_"):].lower()
        try:
            ConnectionRegistry.register(url=vault.get(key), name=db_name)
        except Exception as e:
            print(f"Warning: Failed to register vault database '{db_name}': {e}")

# Caches — scan vault for SERVICE_URL[_ID] keys and register each adapter.
# See _CACHE_BUILDERS at module top for supported services.
_register_caches_from_vault(vault)
# Convenience handle: the unnamed "redis" instance, if present, is exposed
# directly as props["redis"] for views that don't need the registry.
redis = CacheRegistry._adapters.get("redis")
```

Replace with:

```python
vault = Vault(vault_service)
# Vault starts LOCKED. SecurityView unlocks it; vault.unlocked event wires connections.
redis = CacheRegistry._adapters.get("redis")

def _on_vault_unlocked(_event):
    """Re-register vault-sourced DB and cache connections after user unlocks vault."""
    for key in vault.keys():
        if key.startswith("DATABASE_"):
            db_name = key[len("DATABASE_"):].lower()
            try:
                ConnectionRegistry.register(url=vault.get(key), name=db_name)
            except Exception as e:
                print(f"Warning: vault DB '{db_name}': {e}")
    _register_caches_from_vault(vault)

event_bus.subscribe("vault.unlocked", _on_vault_unlocked)
```

**Change B — add `ServiceBackendAdapter` import and construction.** Add to the imports at the top of `main.py`:

```python
from lib.adapters.backend_adapter import ServiceBackendAdapter
from lib.services.user_service import UserService
```

Then after the `user_repo` setup block (around line 120–130), add:

```python
# Backend adapter — the plug between Flet views and the backend.
# Swap ServiceBackendAdapter for HttpBackendAdapter here to switch frontends.
backend = ServiceBackendAdapter(
    factory=ConnectionRegistry.get("postgres") if "postgres" in ConnectionRegistry._factories else
            SessionFactory("sqlite:///./dev.db"),
    user_service=UserService(
        ConnectionRegistry.get("postgres") if "postgres" in ConnectionRegistry._factories else
        SessionFactory("sqlite:///./dev.db")
    ),
    scheduler=scheduler,
)
```

Wait — `scheduler` is defined after the DB block in main.py. Move backend creation to after scheduler is defined. Place this code block right after `scheduler.start()`:

```python
_backend_factory = (
    ConnectionRegistry.get("postgres")
    if "postgres" in ConnectionRegistry._factories
    else SessionFactory("sqlite:///./dev.db")
)
backend = ServiceBackendAdapter(
    factory=_backend_factory,
    user_service=UserService(_backend_factory),
    scheduler=scheduler,
)
```

**Change C — add `backend` to props and register new routes.** In `router.set_props_factory`, add `"backend": backend`:

```python
router.set_props_factory(lambda: {
    "nav":    nav,
    "vault":  vault,
    "events": events,
    "nav_service":   nav_service,
    "vault_service": vault_service,
    "user_repo":         user_repo,
    "redis":             redis,
    "config":            config,
    "connection_tester": connection_tester,
    "cache_tester":      cache_tester,
    "backend":           backend,
    "dev_nav": True,
})
```

And register the three new routes (right after the existing `router.register` calls):

```python
router.register("/manage/users",    "lib.views.manage.users")
router.register("/manage/roles",    "lib.views.manage.roles")
router.register("/admin/scheduler", "lib.views.admin.scheduler")
```

- [ ] **Step 4: Run full suite — no regressions**

```
pytest tests/ -v --tb=short -q
```

Expected: all existing tests pass. `backend` not yet used by any view, no new test file needed for this task.

- [ ] **Step 5: Commit**

```bash
git add main.py lib/views/manage/__init__.py
git commit -m "feat: vault starts locked; vault.unlocked event wires connections; backend adapter in props"
```

---

### Task 5: Login view upgrade

**Files:**
- Modify: `lib/views/login.py`

- [ ] **Step 1: Replace `lib/views/login.py` with the functional version**

The current file is a stub — no auth call. Replace the entire file:

```python
"""Login view — entry point for admin config.

Uses backend.login() which today calls UserService.authenticate_user() directly.
Swap ServiceBackendAdapter for HttpBackendAdapter in main.py to switch to JWT/HTTP
without changing this file.
"""
import flet as ft

from lib.ui.layouts.base_view import BaseView
from lib.ui.components.back_button import BackButton


class LoginView(BaseView):
    title = "Login"
    show_sidebar = False  # login is outside the main app — no sidebar

    def __init__(self, page: ft.Page, props: dict):
        super().__init__(page, props)
        self._backend = props.get("backend")
        self._error_text: ft.Text | None = None
        self._username_field: ft.TextField | None = None
        self._password_field: ft.TextField | None = None

    def _on_sign_in(self, _e):
        username = self._username_field.value.strip()
        password = self._password_field.value.strip()

        if not username or not password:
            self._error_text.value = "Username and password are required."
            self._error_text.update()
            return

        if self._backend is None:
            self._error_text.value = "Backend not available."
            self._error_text.update()
            return

        try:
            self._backend.login(username, password)
            self.nav_service.execute(
                __import__("lib.contracts.base", fromlist=["ActionRequest"])
                .ActionRequest(action="visit", data={"url": "/manage/users"})
            )
        except ValueError:
            self._error_text.value = "Invalid username or password."
            self._error_text.update()

    def build_content(self):
        self._username_field = ft.TextField(label="Username", width=320, autofocus=True)
        self._password_field = ft.TextField(
            label="Password", password=True, can_reveal_password=True, width=320
        )
        self._error_text = ft.Text("", color=ft.Colors.RED_400, size=12)

        return ft.Column(
            [
                ft.Text("Sign In", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("FlexTemplates admin config", size=13, color=ft.Colors.BLUE_GREY_300),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                self._username_field,
                self._password_field,
                self._error_text,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            content=ft.Text("Sign In"),
                            width=150,
                            on_click=self._on_sign_in,
                        ),
                        BackButton(self.nav_service),
                    ],
                    spacing=10,
                ),
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    return LoginView(page, props).render()
```

Note: the import inside `_on_sign_in` avoids a top-level import of `ActionRequest` in the view file. A cleaner alternative is importing at the top of the file, which is preferred:

Replace the method with:

```python
from lib.contracts.base import ActionRequest  # at top of file

    def _on_sign_in(self, _e):
        username = self._username_field.value.strip()
        password = self._password_field.value.strip()

        if not username or not password:
            self._error_text.value = "Username and password are required."
            self._error_text.update()
            return

        if self._backend is None:
            self._error_text.value = "Backend not available."
            self._error_text.update()
            return

        try:
            self._backend.login(username, password)
            self.nav_service.execute(
                ActionRequest(action="visit", data={"url": "/manage/users"})
            )
        except ValueError:
            self._error_text.value = "Invalid username or password."
            self._error_text.update()
```

Full final file:

```python
"""Login view — entry point for admin config.

Uses backend.login() (ServiceBackendAdapter today, HttpBackendAdapter tomorrow).
Swap the adapter in main.py — this file does not change.
"""
import flet as ft

from lib.contracts.base import ActionRequest
from lib.ui.layouts.base_view import BaseView
from lib.ui.components.back_button import BackButton


class LoginView(BaseView):
    title = "Login"
    show_sidebar = False

    def __init__(self, page: ft.Page, props: dict):
        super().__init__(page, props)
        self._backend = props.get("backend")
        self._error_text: ft.Text | None = None
        self._username_field: ft.TextField | None = None
        self._password_field: ft.TextField | None = None

    def _on_sign_in(self, _e):
        username = self._username_field.value.strip()
        password = self._password_field.value.strip()

        if not username or not password:
            self._error_text.value = "Username and password are required."
            self._error_text.update()
            return

        if self._backend is None:
            self._error_text.value = "Backend not available."
            self._error_text.update()
            return

        try:
            self._backend.login(username, password)
            self.nav_service.execute(
                ActionRequest(action="visit", data={"url": "/manage/users"})
            )
        except ValueError:
            self._error_text.value = "Invalid username or password."
            self._error_text.update()

    def build_content(self):
        self._username_field = ft.TextField(label="Username", width=320, autofocus=True)
        self._password_field = ft.TextField(
            label="Password", password=True, can_reveal_password=True, width=320
        )
        self._error_text = ft.Text("", color=ft.Colors.RED_400, size=12)

        return ft.Column(
            [
                ft.Text("Sign In", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("FlexTemplates admin config", size=13, color=ft.Colors.BLUE_GREY_300),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                self._username_field,
                self._password_field,
                self._error_text,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            content=ft.Text("Sign In"),
                            width=150,
                            on_click=self._on_sign_in,
                        ),
                        BackButton(self.nav_service),
                    ],
                    spacing=10,
                ),
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    return LoginView(page, props).render()
```

- [ ] **Step 2: Run full suite — no regressions**

```
pytest tests/ -v --tb=short -q
```

- [ ] **Step 3: Commit**

```bash
git add lib/views/login.py
git commit -m "feat: upgrade login view to call backend.login() with error handling"
```

---

### Task 6: Auth guard on existing views

**Files:**
- Modify: `lib/views/security.py`
- Modify: `lib/views/admin/databases.py`
- Modify: `lib/views/admin/caches.py`

- [ ] **Step 1: Update `lib/views/security.py`**

Two changes:
1. Change `BaseView` → `ProtectedView` in the class definition and import
2. Add `self.events.emit("vault.unlocked", {})` after successful vault unlock in `_unlock_vault()`

Find the import line:
```python
from lib.ui.layouts.base_view import BaseView
```
Add below it:
```python
from lib.ui.layouts.protected_view import ProtectedView
```

Change the class definition from:
```python
class SecurityView(BaseView):
```
To:
```python
class SecurityView(ProtectedView):
```

In the `_unlock_vault` method, find:
```python
        if result.success:
            self._unlock_error = ""
            self._current_state = "unlocked"
            self._load_keys()
            self._refresh_ui()
```
Change to:
```python
        if result.success:
            self._unlock_error = ""
            self._current_state = "unlocked"
            self._load_keys()
            self.events.emit("vault.unlocked", {})
            self._refresh_ui()
```

- [ ] **Step 2: Update `lib/views/admin/databases.py`**

Find:
```python
from lib.ui.layouts.base_view import BaseView
```
Add below it:
```python
from lib.ui.layouts.protected_view import ProtectedView
```

Change:
```python
class AdminDatabasesView(BaseView):
```
To:
```python
class AdminDatabasesView(ProtectedView):
```

- [ ] **Step 3: Update `lib/views/admin/caches.py`**

Find:
```python
from lib.ui.layouts.base_view import BaseView
```
Add below it:
```python
from lib.ui.layouts.protected_view import ProtectedView
```

Change:
```python
class AdminCachesView(BaseView):
```
To:
```python
class AdminCachesView(ProtectedView):
```

- [ ] **Step 4: Run full suite — no regressions**

```
pytest tests/ -v --tb=short -q
```

Note: if existing tests for `AdminDatabasesView` or `AdminCachesView` pass `props` without a `backend` key, they will now get a redirect instead of a rendered view. Check and update any such tests to add `"backend": _MockBackendLoggedIn()` to their props.

- [ ] **Step 5: Commit**

```bash
git add lib/views/security.py lib/views/admin/databases.py lib/views/admin/caches.py
git commit -m "feat: SecurityView + admin views now subclass ProtectedView; emit vault.unlocked on unlock"
```

---

### Task 7: /manage/users view

**Files:**
- Create: `lib/views/manage/users.py`

- [ ] **Step 1: Create `lib/views/manage/users.py`**

```python
"""Manage Users view — paginated list with create and delete."""
from __future__ import annotations

import flet as ft

from lib.ui.components.manage_tabs import ManageTabs
from lib.ui.layouts.protected_view import ProtectedView


class ManageUsersView(ProtectedView):
    title = "Manage Users"
    show_sidebar = True

    def __init__(self, page: ft.Page, props: dict):
        super().__init__(page, props)
        self._backend = props.get("backend")
        self._cur_page = 1
        self._search_query = ""
        self._body: ft.Column | None = None
        # Add-user form fields (assigned in build_content)
        self._new_username: ft.TextField | None = None
        self._new_email: ft.TextField | None = None
        self._new_password: ft.TextField | None = None
        self._form_error: ft.Text | None = None
        self._show_form: bool = False

    # ── Data loading ──────────────────────────────────────────────────────

    def _load_page(self, page_num: int = 1):
        self._cur_page = page_num
        kwargs = {}
        if self._search_query:
            kwargs["username__like"] = f"%{self._search_query}%"
        return self._backend.list_users(page=page_num, page_size=15, **kwargs)

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_search(self, e):
        self._search_query = e.control.value.strip()
        self._refresh_body()

    def _on_prev(self, _e):
        if self._cur_page > 1:
            self._refresh_body(self._cur_page - 1)

    def _on_next(self, _e, total_pages: int):
        if self._cur_page < total_pages:
            self._refresh_body(self._cur_page + 1)

    def _on_delete(self, user_id: str, username: str):
        self._backend.delete_user(user_id)
        self._refresh_body()
        self._snack(f"Deleted {username}")

    def _on_toggle_form(self, _e):
        self._show_form = not self._show_form
        self._refresh_body()

    def _on_add_user(self, _e):
        username = self._new_username.value.strip()
        email = self._new_email.value.strip()
        password = self._new_password.value.strip()

        if not username or not email or not password:
            self._form_error.value = "All fields are required."
            self._form_error.update()
            return

        try:
            self._backend.create_user({"username": username, "email": email, "password": password})
            self._show_form = False
            self._refresh_body()
            self._snack(f"Created {username}")
        except Exception as exc:
            self._form_error.value = str(exc)
            self._form_error.update()

    # ── UI builders ───────────────────────────────────────────────────────

    def _build_table(self, result: dict) -> ft.Control:
        rows = []
        for user in result["items"]:
            roles_text = ", ".join(user.get("roles", [])) if user.get("roles") else "—"
            rows.append(ft.DataRow([
                ft.DataCell(ft.Text(user["username"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(user.get("email", ""), size=12)),
                ft.DataCell(ft.Text(roles_text, size=12, color=ft.Colors.BLUE_GREY_300)),
                ft.DataCell(
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_size=18,
                        icon_color=ft.Colors.RED_300,
                        tooltip=f"Delete {user['username']}",
                        on_click=lambda _e, uid=user["id"], uname=user["username"]:
                            self._on_delete(uid, uname),
                    )
                ),
            ]))

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Username")),
                ft.DataColumn(ft.Text("Email")),
                ft.DataColumn(ft.Text("Roles")),
                ft.DataColumn(ft.Text("")),
            ],
            rows=rows,
        )

        total_pages = result["pages"]
        page_label = ft.Text(f"Page {result['page']} of {total_pages}  ({result['total']} total)",
                             size=12, color=ft.Colors.BLUE_GREY_300)

        pagination = ft.Row([
            ft.TextButton(
                content=ft.Text("← Prev"),
                disabled=result["page"] <= 1,
                on_click=self._on_prev,
            ),
            page_label,
            ft.TextButton(
                content=ft.Text("Next →"),
                disabled=result["page"] >= total_pages,
                on_click=lambda e, tp=total_pages: self._on_next(e, tp),
            ),
        ], spacing=8)

        return ft.Column([table, pagination], spacing=8)

    def _build_add_form(self) -> ft.Control:
        self._new_username = ft.TextField(label="Username", width=200)
        self._new_email = ft.TextField(label="Email", width=220)
        self._new_password = ft.TextField(label="Password", password=True, width=180)
        self._form_error = ft.Text("", color=ft.Colors.RED_400, size=12)

        return ft.Container(
            content=ft.Column([
                ft.Text("New User", size=14, weight=ft.FontWeight.BOLD),
                ft.Row([self._new_username, self._new_email, self._new_password], spacing=10),
                ft.Row([
                    ft.ElevatedButton(content=ft.Text("Create"), on_click=self._on_add_user),
                    ft.TextButton(content=ft.Text("Cancel"), on_click=self._on_toggle_form),
                ], spacing=8),
                self._form_error,
            ], spacing=8),
            bgcolor=ft.Colors.BLUE_GREY_900,
            border_radius=8,
            padding=16,
        )

    def _refresh_body(self, page_num: int | None = None):
        if self._body is None:
            return
        page_num = page_num or self._cur_page
        result = self._load_page(page_num)
        controls = [self._build_table(result)]
        if self._show_form:
            controls.append(self._build_add_form())
        self._body.controls = controls
        self._body.update()

    def _snack(self, message: str):
        snack = ft.SnackBar(content=ft.Text(message), duration=1500)
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    # ── Layout ────────────────────────────────────────────────────────────

    def build_content(self):
        tabs = ManageTabs(self.page.route or "/manage/users", self.nav_service)

        search = ft.TextField(
            label="Search by username",
            width=280,
            on_change=self._on_search,
            prefix_icon=ft.Icons.SEARCH,
        )
        add_btn = ft.ElevatedButton(
            content=ft.Text("+ Add User"),
            on_click=self._on_toggle_form,
        )
        toolbar = ft.Row([search, add_btn], spacing=12)

        result = self._load_page(1)
        self._body = ft.Column([self._build_table(result)], spacing=8)

        return ft.Column([tabs, toolbar, self._body], spacing=16)


def view(page: ft.Page, props: dict) -> ft.View:
    return ManageUsersView(page, props).render()
```

- [ ] **Step 2: Run full suite — no regressions**

```
pytest tests/ -v --tb=short -q
```

- [ ] **Step 3: Commit**

```bash
git add lib/views/manage/users.py
git commit -m "feat: /manage/users view — paginated list, search, create, delete"
```

---

### Task 8: /manage/roles view

**Files:**
- Create: `lib/views/manage/roles.py`

- [ ] **Step 1: Create `lib/views/manage/roles.py`**

```python
"""Manage Roles view — list, create, delete."""
from __future__ import annotations

import flet as ft

from lib.ui.components.manage_tabs import ManageTabs
from lib.ui.layouts.protected_view import ProtectedView


class ManageRolesView(ProtectedView):
    title = "Manage Roles"
    show_sidebar = True

    def __init__(self, page: ft.Page, props: dict):
        super().__init__(page, props)
        self._backend = props.get("backend")
        self._body: ft.Column | None = None
        self._role_name_field: ft.TextField | None = None
        self._error_text: ft.Text | None = None

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_create_role(self, _e):
        name = self._role_name_field.value.strip()
        if not name:
            self._error_text.value = "Role name is required."
            self._error_text.update()
            return

        try:
            self._backend.create_role(name)
            self._role_name_field.value = ""
            self._error_text.value = ""
            self._refresh_body()
            self._snack(f"Role '{name}' created")
        except Exception as exc:
            self._error_text.value = str(exc)
            self._error_text.update()

    def _on_delete_role(self, role_id: str, name: str):
        self._backend.delete_role(role_id)
        self._refresh_body()
        self._snack(f"Role '{name}' deleted")

    # ── UI builders ───────────────────────────────────────────────────────

    def _build_table(self, roles: list[dict]) -> ft.Control:
        if not roles:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.VERIFIED_USER, size=36, color=ft.Colors.BLUE_GREY_400),
                    ft.Text("No roles defined yet.", size=14, color=ft.Colors.BLUE_GREY_300),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=30,
                bgcolor=ft.Colors.BLUE_GREY_900,
                border_radius=8,
                alignment=ft.Alignment(0, 0),
            )

        rows = [
            ft.DataRow([
                ft.DataCell(ft.Text(r["name"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(r.get("description") or "—", size=12,
                                    color=ft.Colors.BLUE_GREY_300)),
                ft.DataCell(
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_size=18,
                        icon_color=ft.Colors.RED_300,
                        tooltip=f"Delete {r['name']}",
                        on_click=lambda _e, rid=r["id"], rname=r["name"]:
                            self._on_delete_role(rid, rname),
                    )
                ),
            ])
            for r in roles
        ]

        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Name")),
                ft.DataColumn(ft.Text("Description")),
                ft.DataColumn(ft.Text("")),
            ],
            rows=rows,
        )

    def _refresh_body(self):
        if self._body is None:
            return
        roles = self._backend.list_roles()
        self._body.controls = [self._build_table(roles)]
        self._body.update()

    def _snack(self, message: str):
        snack = ft.SnackBar(content=ft.Text(message), duration=1500)
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    # ── Layout ────────────────────────────────────────────────────────────

    def build_content(self):
        tabs = ManageTabs(self.page.route or "/manage/roles", self.nav_service)

        self._role_name_field = ft.TextField(label="Role name", width=240, autofocus=False)
        self._error_text = ft.Text("", color=ft.Colors.RED_400, size=12)

        create_row = ft.Row([
            self._role_name_field,
            ft.ElevatedButton(content=ft.Text("+ Create"), on_click=self._on_create_role),
            self._error_text,
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        roles = self._backend.list_roles()
        self._body = ft.Column([self._build_table(roles)], spacing=8)

        return ft.Column([tabs, create_row, ft.Divider(height=16), self._body], spacing=8)


def view(page: ft.Page, props: dict) -> ft.View:
    return ManageRolesView(page, props).render()
```

- [ ] **Step 2: Run full suite — no regressions**

```
pytest tests/ -v --tb=short -q
```

- [ ] **Step 3: Commit**

```bash
git add lib/views/manage/roles.py
git commit -m "feat: /manage/roles view — list, create, delete"
```

---

### Task 9: /admin/scheduler view

**Files:**
- Create: `lib/views/admin/scheduler.py`

- [ ] **Step 1: Create `lib/views/admin/scheduler.py`**

```python
"""Scheduler admin view — read-only inspector for registered APScheduler jobs."""
from __future__ import annotations

import flet as ft

from lib.ui.components.admin_tabs import AdminTabs
from lib.ui.layouts.protected_view import ProtectedView


class AdminSchedulerView(ProtectedView):
    title = "Scheduler"
    show_sidebar = True

    def __init__(self, page: ft.Page, props: dict):
        super().__init__(page, props)
        self._backend = props.get("backend")
        self._body: ft.Column | None = None

    # ── UI builders ───────────────────────────────────────────────────────

    def _build_table(self, jobs: list[dict]) -> ft.Control:
        if not jobs:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SCHEDULE, size=42, color=ft.Colors.BLUE_GREY_400),
                    ft.Text("No jobs scheduled", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Add jobs in main.py via scheduler.add_job(fn, trigger, ...)",
                        size=12, color=ft.Colors.BLUE_GREY_300,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=40,
                bgcolor=ft.Colors.BLUE_GREY_900,
                border_radius=12,
                alignment=ft.Alignment(0, 0),
            )

        rows = [
            ft.DataRow([
                ft.DataCell(ft.Text(j["id"], size=12, color=ft.Colors.BLUE_GREY_300)),
                ft.DataCell(ft.Text(j["func_name"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(j["trigger"], size=12)),
                ft.DataCell(ft.Text(j["next_run_time"], size=12)),
            ])
            for j in jobs
        ]

        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Job ID")),
                ft.DataColumn(ft.Text("Function")),
                ft.DataColumn(ft.Text("Trigger")),
                ft.DataColumn(ft.Text("Next Run")),
            ],
            rows=rows,
        )

    def _refresh_body(self):
        if self._body is None:
            return
        jobs = self._backend.list_jobs()
        self._body.controls = [self._build_table(jobs)]
        self._body.update()
        self.page.update()

    # ── Layout ────────────────────────────────────────────────────────────

    def build_content(self):
        tabs = AdminTabs(self.page.route or "/admin/scheduler", self.nav_service)

        header = ft.Row([
            ft.Column([
                ft.Text("Scheduled Jobs", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Read-only — add/remove jobs in main.py",
                        size=12, color=ft.Colors.BLUE_GREY_300),
            ], spacing=2, expand=True),
            ft.TextButton(
                content=ft.Text("↺  Refresh"),
                on_click=lambda _: self._refresh_body(),
            ),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        jobs = self._backend.list_jobs()
        self._body = ft.Column([self._build_table(jobs)], spacing=8)

        return ft.Column([tabs, header, ft.Container(height=8), self._body], spacing=0)


def view(page: ft.Page, props: dict) -> ft.View:
    return AdminSchedulerView(page, props).render()
```

- [ ] **Step 2: Run full suite — no regressions**

```
pytest tests/ -v --tb=short -q
```

- [ ] **Step 3: Commit**

```bash
git add lib/views/admin/scheduler.py
git commit -m "feat: /admin/scheduler view — read-only job inspector"
```

---

### Task 10: Smoke test update + final check

**Files:**
- Modify: `tests/test_smoke.py`

- [ ] **Step 1: Read the current smoke test**

Open `tests/test_smoke.py` and find the list of modules being imported (they will be in a pytest `parametrize` or a list).

- [ ] **Step 2: Add new modules**

Add these four entries to the module import list in the smoke test:

```python
"lib.adapters.backend_adapter",
"lib.ui.layouts.protected_view",
"lib.ui.components.manage_tabs",
"lib.views.manage.users",
"lib.views.manage.roles",
"lib.views.admin.scheduler",
```

- [ ] **Step 3: Run the smoke test**

```
pytest tests/test_smoke.py -v
```

Expected: all smoke test cases pass (all new modules import without error).

- [ ] **Step 4: Run the full suite**

```
pytest tests/ -v --tb=short -q
```

Expected: all tests pass. Record the final test count — should be higher than 373.

- [ ] **Step 5: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: smoke test covers Phase 4 new modules"
```

- [ ] **Step 6: Push to v2 branch**

```bash
git push origin main:v2
```

---

## Self-review Checklist (for the implementer)

Before marking complete, verify:

- [ ] `pytest tests/ -q` is fully green
- [ ] No view file imports a service class directly (`grep -r "from lib.services" lib/views/` returns nothing new)
- [ ] No view file imports a repository class directly (`grep -r "from lib.repositories" lib/views/` returns nothing new)
- [ ] `vault.unlock()` is gone from `main.py`
- [ ] `"backend"` key is present in the `props_factory` lambda in `main.py`
- [ ] All three new routes are registered in `main.py`
