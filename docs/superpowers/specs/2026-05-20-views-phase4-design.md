# Phase 4 Views — Implementation Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Login, Manage (Users + Roles), and Scheduler admin views, wired through a swappable `BackendAdapter` layer so the Flet frontend can be replaced with any other frontend without touching the backend.

**Architecture:** `IBackendAdapter` is the plug between the Flet UI and the backend. `ServiceBackendAdapter` is today's concrete implementation — it calls services directly (no HTTP). When a web or mobile frontend is needed, swap it for `HttpBackendAdapter` in `main.py` and nothing else changes. Views depend only on the interface.

**Tech Stack:** Flet 0.84+, FastAPI, SQLAlchemy, APScheduler, pydantic-settings, existing FlexTemplates contracts

---

## Core Principle

> "One day the client wants the same Flet app but in HTML — we just swap the frontend, not the whole app."

Every view in this phase calls `self.props["backend"]` — an `IBackendAdapter` instance. The adapter owns session state and all data access. Views never import services, never call repositories, never read vault secrets.

The vault enforces this at the infrastructure level: it starts **locked**. No code auto-unlocks it. The user must explicitly unlock via the Security view. The `vault.unlocked` event then signals `main.py` to wire vault-sourced connections.

---

## The `BackendAdapter` Layer

### `IBackendAdapter` — `lib/adapters/backend_adapter.py`

Abstract base class. All views depend on this interface only.

```python
from abc import ABC, abstractmethod

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
        """Returns paginate() shape: {items, total, page, page_size, pages}"""

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
    # Wired in Phase 4 interface; UI control deferred to Phase 5

    @abstractmethod
    def remove_role(self, user_id: str, role_id: str) -> bool: ...
    # Wired in Phase 4 interface; UI control deferred to Phase 5

    # ── Scheduler ─────────────────────────────────────────────────────────
    @abstractmethod
    def list_jobs(self) -> list[dict]:
        """Returns list of {id, name, trigger, next_run_time, func_name}"""
```

### `ServiceBackendAdapter` — same file

Today's implementation. Calls `UserService`, `RoleRepository`, and `TaskScheduler` directly. Stores session in `self._session: dict | None`.

```python
class ServiceBackendAdapter(IBackendAdapter):
    def __init__(self, factory, user_service, role_repo, scheduler):
        self._factory      = factory       # SessionFactory — for repo instantiation
        self._user_service = user_service
        self._role_repo    = role_repo
        self._scheduler    = scheduler
        self._session: dict | None = None

    def login(self, username, password):
        user = self._user_service.authenticate_user(username, password)
        self._session = user   # {"id", "username", "email", "roles"}
        return {"user": user}

    def logout(self):
        self._session = None

    def current_user(self):
        return self._session

    def list_users(self, page=1, page_size=20, **filters):
        repo = UserRepository(self._factory)
        return repo.paginate(page=page, page_size=page_size)

    # ... remaining methods follow the same pattern — one per interface method
```

### Future `HttpBackendAdapter` (not built now, documented for reference)

```python
class HttpBackendAdapter(IBackendAdapter):
    def __init__(self, base_url: str):
        self._base = base_url
        self._token: str | None = None

    def login(self, username, password):
        r = httpx.post(f"{self._base}/auth/login",
                       data={"username": username, "password": password})
        r.raise_for_status()
        self._token = r.json()["access_token"]
        # decode token for current_user() ...

    def list_users(self, page=1, page_size=20, **filters):
        r = httpx.get(f"{self._base}/users",
                      params={"page": page, "page_size": page_size},
                      headers=self._auth_header())
        return r.json()
```

Swap `ServiceBackendAdapter` for `HttpBackendAdapter` in `main.py` — zero view changes.

---

## Auth Guard — `ProtectedView`

### `lib/ui/layouts/protected_view.py`

```python
from lib.ui.layouts.base_view import BaseView
from lib.contracts.base import ActionRequest
import flet as ft

class ProtectedView(BaseView):
    """Subclass instead of BaseView for views that require login.
    Redirects to /login if backend.current_user() returns None.
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

Views that require auth subclass `ProtectedView`. Views that don't (`LoginView`, `HomeView`, `ProductsView`, `NotFoundView`) stay on `BaseView`.

**Protected views:** `SecurityView`, `ManageUsersView`, `ManageRolesView`, `AdminSchedulerView`, `AdminDatabasesView`, `AdminCachesView`

---

## Vault — Remove Auto-Unlock, Add Event

### `main.py` change

Remove:
```python
vault.unlock()   # ← DELETE THIS
```

Add event subscription after `event_bus` is created:
```python
def _on_vault_unlocked(event):
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

### `lib/views/security.py` change

After successful vault unlock, publish the event:
```python
if result.success:
    self._current_state = "unlocked"
    self._load_keys()
    self.events.emit("vault.unlocked", {})   # triggers connection wiring in main.py
    self._refresh_ui()
```

The Security view does not know what happens downstream. The event is a signal — "vault is open, do what you need." Connection registration is `main.py`'s concern.

---

## Navigation Structure

### `SIDEBAR_ITEMS` (updated in `base_view.py`)

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

### `ManageTabs` — `lib/ui/components/manage_tabs.py`

Pill bar mirroring `AdminTabs`:
```
[ Users ]  [ Roles ]
```

### `AdminTabs` — add Scheduler pill

```
[ Databases ]  [ Caches ]  [ Scheduler ]
```

### Routes registered in `main.py`

```python
router.register("/manage/users",    "lib.views.manage.users")
router.register("/manage/roles",    "lib.views.manage.roles")
router.register("/admin/scheduler", "lib.views.admin.scheduler")
```

---

## View Designs

### `/login` — upgrade existing stub

`LoginView(BaseView)` — no auth guard (it IS the auth entry point).

**Flow:**
1. Username + password fields + Sign In button
2. On submit: `backend.login(username, password)`
3. Success → `nav.go("/manage/users")`
4. Failure → inline error text below the form

**Props used:** `backend`

**No JWT, no httpx.** `ServiceBackendAdapter.login()` calls `UserService.authenticate_user()` and stores session in `self._session`. When `HttpBackendAdapter` is swapped in, the same login view works unchanged.

---

### `/manage/users` — `lib/views/manage/users.py`

`ManageUsersView(ProtectedView)`

**Layout:**
```
ManageTabs (Users | Roles)
─────────────────────────────────────
[Search: ___________] [+ Add User]

 Username      Email           Roles   Actions
 alice         alice@…         admin   [🗑]
 bob           bob@…           —       [🗑]

 ← 1 of 3 →   (pagination controls)
```

**Features:**
- `backend.list_users(page, page_size)` on load and page change
- Filter by username via `backend.list_users(username__icontains=query)`
- Add User: inline form (username, email, password) → `backend.create_user(data)`
- Delete: confirmation snackbar → `backend.delete_user(id)`
- Pagination: prev/next buttons, current page display

**Dev note:** Works with SQLite dev fallback. No PostgreSQL required.

---

### `/manage/roles` — `lib/views/manage/roles.py`

`ManageRolesView(ProtectedView)`

**Layout:**
```
ManageTabs (Users | Roles)
─────────────────────────────────────
[Role name: ___________] [+ Create]

 Name       Users with role   Actions
 admin      2                 [🗑]
 viewer     5                 [🗑]
```

**Features:**
- `backend.list_roles()` on load
- Create role: text field → `backend.create_role(name)`
- Delete role: `backend.delete_role(id)` (no confirmation needed — roles have no secrets)
- `assign_role` / `remove_role` are defined in `IBackendAdapter` and implemented in `ServiceBackendAdapter`, but no UI control is wired in this phase — those buttons are a Phase 5 addition

---

### `/admin/scheduler` — `lib/views/admin/scheduler.py`

`AdminSchedulerView(ProtectedView)`

**Layout:**
```
AdminTabs (Databases | Caches | Scheduler)
─────────────────────────────────────────
Scheduled Jobs                    [↺ Refresh]

 Job ID       Function         Trigger       Next Run
 cleanup-1    cleanup_temp     interval/6h   2026-05-20 18:00
 report-1     send_report      cron 09:00    2026-05-21 09:00

 (No jobs registered — add via scheduler.add_job() in main.py)
```

**Features:**
- `backend.list_jobs()` on load and on Refresh click
- Read-only. No add/remove/pause from UI — those are code-defined
- Empty state when no jobs registered
- `list_jobs()` in `ServiceBackendAdapter` reads from `scheduler.get_jobs()` (APScheduler API)

**Extensibility:** `IBackendAdapter.list_jobs()` is the hook. When job control is needed, add `pause_job(id)`, `resume_job(id)`, `remove_job(id)` to the interface — no view changes for read-only consumers.

---

## Files Summary

### Create

| File | Purpose |
|---|---|
| `lib/adapters/backend_adapter.py` | `IBackendAdapter` ABC + `ServiceBackendAdapter` |
| `lib/ui/layouts/protected_view.py` | `ProtectedView(BaseView)` auth guard |
| `lib/ui/components/manage_tabs.py` | ManageTabs pill bar |
| `lib/views/manage/__init__.py` | empty |
| `lib/views/manage/users.py` | Paginated user list + create + delete |
| `lib/views/manage/roles.py` | Role list + create + delete |
| `lib/views/admin/scheduler.py` | Read-only scheduler inspector |

### Modify

| File | Change |
|---|---|
| `main.py` | Remove `vault.unlock()`. Subscribe `vault.unlocked`. Add `ServiceBackendAdapter` to props. Register 3 new routes. |
| `lib/views/login.py` | Upgrade stub — call `backend.login()`, redirect on success, show error on failure |
| `lib/views/security.py` | Subclass `ProtectedView`. Publish `vault.unlocked` event after successful unlock. |
| `lib/views/admin/databases.py` | Subclass `ProtectedView` |
| `lib/views/admin/caches.py` | Subclass `ProtectedView` |
| `lib/ui/layouts/base_view.py` | Add `("Manage", "/manage/users")` to `SIDEBAR_ITEMS` |
| `lib/ui/components/admin_tabs.py` | Add Scheduler pill to `ADMIN_TABS` |

---

## What Does Not Change

- `lib/contracts/` — no new contracts needed; views use the adapter, not `ActionRequest` directly
- `lib/services/` — untouched; `ServiceBackendAdapter` calls them, views do not
- `lib/repositories/` — untouched
- `lib/api/routes/` — untouched; HTTP API remains independent of these views
- `lib/security/vault_service.py` — untouched; SecurityView calls it through `props["vault_service"]`
- All existing tests — no regressions expected

---

## Testing Notes

- New views tested with a `FakePage` + `ServiceBackendAdapter` wired to in-memory SQLite (same pattern as existing view tests)
- `ProtectedView` redirect tested by passing a backend with `current_user() = None`
- `vault.unlocked` event handler tested by subscribing in a test and asserting `ConnectionRegistry` receives the registration
- Scheduler view tested with a real `TaskScheduler` instance with a dummy job registered
