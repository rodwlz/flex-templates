# Phase 5B — Adapter Decomposition

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `ServiceBackendAdapter` into four domain sub-adapters (`auth`, `users`, `roles`, `scheduler`) so adding a new entity never requires touching a growing central file.

**Architecture:** `IBackendAdapter` becomes a map of four typed domain properties. Each domain lives in its own file with its own interface. Views migrate from flat calls (`backend.list_users()`) to namespaced calls (`backend.users.list()`). `ServiceBackendAdapter` becomes a thin coordinator that owns construction of the four sub-adapters.

**Tech Stack:** Python ABCs, existing SQLAlchemy session factory, existing service layer — no new dependencies.

---

## The Problem

`ServiceBackendAdapter` currently owns authentication state, user CRUD, role management, and scheduler queries in a single 154-line class. Adding any new entity (orders, products, reports) grows this file further. It has no clear boundaries — auth state (`_session`) sits alongside unrelated repo calls.

---

## Design

### Domain interfaces (new files)

Each domain gets its own ABC with only the methods that belong to it. Method names drop the entity prefix — the namespace provides context.

**`lib/adapters/auth_adapter.py`**
```python
class IAuthAdapter(ABC):
    @abstractmethod
    def login(self, username: str, password: str) -> dict:
        """Returns {"user": {id, username, email, roles}} on success.
        Raises ValueError on bad credentials."""

    @abstractmethod
    def logout(self) -> None: ...

    @abstractmethod
    def current_user(self) -> dict | None:
        """Returns logged-in user dict or None if not authenticated."""


class ServiceAuthAdapter(IAuthAdapter):
    def __init__(self, user_service):
        self._user_service = user_service
        self._session: dict | None = None

    def login(self, username: str, password: str) -> dict:
        user = self._user_service.authenticate_user(username, password)
        self._session = user
        return {"user": user}

    def logout(self) -> None:
        self._session = None

    def current_user(self) -> dict | None:
        return self._session
```

**`lib/adapters/users_adapter.py`**
```python
class IUserAdapter(ABC):
    @abstractmethod
    def list(self, page: int = 1, page_size: int = 20) -> dict:
        """Returns paginate() shape: {items, total, page, page_size, pages}.
        Items are dicts with string UUIDs, no password_hash."""

    @abstractmethod
    def create(self, data: dict) -> dict: ...

    @abstractmethod
    def delete(self, user_id: str) -> bool: ...


class ServiceUserAdapter(IUserAdapter):
    def __init__(self, factory, user_service):
        self._factory = factory
        self._user_service = user_service

    def list(self, page: int = 1, page_size: int = 20) -> dict:
        repo = UserRepository(self._factory)
        result = repo.paginate(page=page, page_size=page_size)
        result["items"] = [_str_uuids(item) for item in result["items"]]
        return result

    def create(self, data: dict) -> dict:
        return self._user_service.create_user(
            username=data["username"],
            email=data["email"],
            password=data.get("password", ""),
        )

    def delete(self, user_id: str) -> bool:
        return self._user_service.delete_user(user_id)
```

**`lib/adapters/roles_adapter.py`**
```python
class IRoleAdapter(ABC):
    @abstractmethod
    def list(self) -> list[dict]: ...

    @abstractmethod
    def create(self, name: str) -> dict: ...

    @abstractmethod
    def delete(self, role_id: str) -> bool: ...

    @abstractmethod
    def assign(self, user_id: str, role_id: str) -> bool: ...

    @abstractmethod
    def remove(self, user_id: str, role_id: str) -> bool: ...


class ServiceRoleAdapter(IRoleAdapter):
    def __init__(self, factory):
        self._factory = factory

    def list(self) -> list[dict]:
        repo = RoleRepository(self._factory)
        return [_str_uuids(r) for r in repo.filter_by()]

    def create(self, name: str) -> dict:
        repo = RoleRepository(self._factory)
        role = repo.create({"name": name})
        return {"id": str(role.id), "name": role.name}

    def delete(self, role_id: str) -> bool:
        repo = RoleRepository(self._factory)
        return repo.delete(uuid.UUID(role_id))

    def assign(self, user_id: str, role_id: str) -> bool:
        repo = UserRepository(self._factory)
        return repo.add_role(uuid.UUID(user_id), uuid.UUID(role_id))

    def remove(self, user_id: str, role_id: str) -> bool:
        repo = UserRepository(self._factory)
        return repo.remove_role(uuid.UUID(user_id), uuid.UUID(role_id))
```

**`lib/adapters/scheduler_adapter.py`**
```python
class ISchedulerAdapter(ABC):
    @abstractmethod
    def list(self) -> list[dict]:
        """Returns [{id, name, trigger, next_run_time, func_name}, ...]"""


class ServiceSchedulerAdapter(ISchedulerAdapter):
    def __init__(self, scheduler=None):
        self._scheduler = scheduler

    def list(self) -> list[dict]:
        if self._scheduler is None:
            return []
        jobs = self._scheduler.get_jobs()
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

### Shared utility

`_str_uuids` moves out of `backend_adapter.py` into a dedicated utilities file so all domain adapters can import it without circular deps.

**`lib/adapters/_utils.py`**
```python
import uuid

def _str_uuids(d: dict) -> dict:
    """Stringify any uuid.UUID values in *d* so views get plain strings."""
    return {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in d.items()}
```

### Coordinator (updated `backend_adapter.py`)

`IBackendAdapter` becomes a map of four domain properties. `ServiceBackendAdapter` constructs the four sub-adapters and exposes them.

```python
class IBackendAdapter(ABC):
    @property
    @abstractmethod
    def auth(self) -> IAuthAdapter: ...

    @property
    @abstractmethod
    def users(self) -> IUserAdapter: ...

    @property
    @abstractmethod
    def roles(self) -> IRoleAdapter: ...

    @property
    @abstractmethod
    def scheduler(self) -> ISchedulerAdapter: ...


class ServiceBackendAdapter(IBackendAdapter):
    def __init__(self, factory, user_service, scheduler=None):
        self._auth      = ServiceAuthAdapter(user_service)
        self._users     = ServiceUserAdapter(factory, user_service)
        self._roles     = ServiceRoleAdapter(factory)
        self._scheduler = ServiceSchedulerAdapter(scheduler)

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

### View call-site migration

11 call sites across 5 files, all mechanical renames:

| Old call | New call |
|---|---|
| `backend.login(u, p)` | `backend.auth.login(u, p)` |
| `backend.logout()` | `backend.auth.logout()` |
| `backend.current_user()` | `backend.auth.current_user()` |
| `backend.list_users(page=p, page_size=n)` | `backend.users.list(page=p, page_size=n)` |
| `backend.create_user(data)` | `backend.users.create(data)` |
| `backend.delete_user(id)` | `backend.users.delete(id)` |
| `backend.list_roles()` | `backend.roles.list()` |
| `backend.create_role(name)` | `backend.roles.create(name)` |
| `backend.delete_role(id)` | `backend.roles.delete(id)` |
| `backend.assign_role(uid, rid)` | `backend.roles.assign(uid, rid)` |
| `backend.remove_role(uid, rid)` | `backend.roles.remove(uid, rid)` |
| `backend.list_jobs()` | `backend.scheduler.list()` |

Files touched: `lib/ui/layouts/protected_view.py`, `lib/views/login.py`, `lib/views/manage/users.py`, `lib/views/manage/roles.py`, `lib/views/admin/scheduler.py`.

### Adding a future entity

1. Create `lib/adapters/orders_adapter.py` — `IOrderAdapter` + `ServiceOrderAdapter`
2. Add `orders` property to `IBackendAdapter` (one abstract property)
3. Add `self._orders = ServiceOrderAdapter(factory, order_service)` + `orders` property to `ServiceBackendAdapter`
4. That is all — no existing file grows

---

## Security Tests

These tests verify that domain adapters never leak sensitive fields and handle invalid input gracefully.

**Auth adapter:**
- `test_auth_login_response_has_no_password_hash` — login success: returned dict must not contain `password_hash` or `salt`
- `test_auth_current_user_none_on_fresh_adapter` — `current_user()` returns `None` before any login
- `test_auth_logout_clears_session` — after login then logout, `current_user()` is `None`
- `test_auth_login_failure_leaks_no_user_data` — wrong password raises `ValueError`; `current_user()` remains `None`

**User adapter:**
- `test_users_list_items_have_no_password_hash` — every item in `list()` result must not contain `password_hash`
- `test_users_create_response_has_no_password_hash` — `create()` response must not contain `password_hash`

**Role adapter:**
- `test_roles_assign_nonexistent_user_returns_false` — `assign()` with random UUID user returns `False`
- `test_roles_assign_nonexistent_role_returns_false` — `assign()` with random UUID role returns `False`
- `test_roles_delete_nonexistent_returns_false` — `delete()` with random UUID returns `False`
- `test_roles_remove_role_not_assigned_returns_false` — `remove()` when role was never assigned returns `False`

---

## Files

| File | Action |
|---|---|
| `lib/adapters/_utils.py` | Create — `_str_uuids` helper |
| `lib/adapters/auth_adapter.py` | Create — `IAuthAdapter` + `ServiceAuthAdapter` |
| `lib/adapters/users_adapter.py` | Create — `IUserAdapter` + `ServiceUserAdapter` |
| `lib/adapters/roles_adapter.py` | Create — `IRoleAdapter` + `ServiceRoleAdapter` |
| `lib/adapters/scheduler_adapter.py` | Create — `ISchedulerAdapter` + `ServiceSchedulerAdapter` |
| `lib/adapters/backend_adapter.py` | Modify — replace flat methods with 4 domain properties |
| `lib/ui/layouts/protected_view.py` | Modify — `backend.current_user()` → `backend.auth.current_user()` |
| `lib/views/login.py` | Modify — `backend.login()` → `backend.auth.login()` |
| `lib/views/manage/users.py` | Modify — 3 call sites |
| `lib/views/manage/roles.py` | Modify — 4 call sites |
| `lib/views/admin/scheduler.py` | Modify — 2 call sites |
| `tests/test_backend_adapter.py` | Modify — update all calls to namespaced form; add security tests |
| `tests/test_protected_view.py` | Modify — mock must expose `.auth.current_user()` |
| `tests/test_login_view.py` | Modify — mock must expose `.auth.login()` |
| `tests/test_manage_users_view.py` | Modify — mock must expose `.users.*` |
| `tests/test_manage_roles_view.py` | Modify — mock must expose `.roles.*` |
| `tests/test_admin_scheduler_view.py` | Modify — mock must expose `.scheduler.list()` |
| `tests/test_smoke.py` | Modify — add 5 new module imports |

---

## Tests — Complete Inventory

### Domain adapter unit tests (new file: `tests/test_domain_adapters.py`)

```
test_auth_login_stores_session
test_auth_login_response_has_no_password_hash      ← security
test_auth_current_user_none_on_fresh_adapter       ← security
test_auth_logout_clears_session                    ← security
test_auth_login_failure_leaks_no_user_data         ← security
test_users_list_returns_paginate_shape
test_users_list_items_have_no_password_hash        ← security
test_users_create_returns_dict_with_id
test_users_create_response_has_no_password_hash    ← security
test_users_delete_returns_true
test_users_delete_nonexistent_returns_false
test_roles_list_empty_initially
test_roles_create_returns_dict
test_roles_delete_returns_true
test_roles_assign_and_remove
test_roles_assign_nonexistent_user_returns_false   ← security
test_roles_assign_nonexistent_role_returns_false   ← security
test_roles_delete_nonexistent_returns_false        ← security
test_roles_remove_role_not_assigned_returns_false  ← security
test_scheduler_list_empty_without_scheduler
test_scheduler_list_returns_registered_job
```

### Coordinator tests (updated `tests/test_backend_adapter.py`)

All existing tests preserved, calls migrated to namespaced form. No net new tests needed here — domain adapter tests cover the logic.

### View mock updates

Existing view tests use `MagicMock` — they need `mock.auth.current_user.return_value`, `mock.users.list.return_value`, etc. This is a mechanical update, no new test logic.

---

## Build Order

1. `lib/adapters/_utils.py` — shared helper (no deps)
2. `lib/adapters/auth_adapter.py` — auth domain
3. `lib/adapters/users_adapter.py` — users domain
4. `lib/adapters/roles_adapter.py` — roles domain
5. `lib/adapters/scheduler_adapter.py` — scheduler domain
6. `lib/adapters/backend_adapter.py` — coordinator rewrite; all existing adapter tests go red
7. `tests/test_domain_adapters.py` — 21 tests; all pass
8. `tests/test_backend_adapter.py` — migrate calls; all pass
9. View files (5) — migrate 15 call sites
10. View test files (5) — update mock shapes
11. `tests/test_smoke.py` — add 5 new imports

All 451 existing tests must still pass after every step.
