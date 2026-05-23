# Phase 5A — Framework Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `_serialize`/`_deserialize` hooks to `AbstractRepository`, a typed `ViewContext` to `BaseView`, and a brute-force delay to the auth login route.

**Architecture:** Pure additions — existing methods route through new overridable hooks; `BaseView` gains `self.ctx` alongside the untouched `self.props`; the auth route becomes async with a 500ms sleep on failure only. Nothing breaks; all 434 existing tests must still pass after every task.

**Tech Stack:** Python dataclasses, SQLAlchemy `inspect`, FastAPI async routes, pytest timing assertions.

---

## File Map

| File | Change |
|---|---|
| `lib/repositories/base.py` | Add `_serialize()`, `_deserialize()`; update `paginate()`, `filter_by()`, `create()`, `update()`; remove `_obj_to_dict` |
| `lib/repositories/user_repository.py` | Replace 20-line `paginate()` override with 8-line `_serialize()` + `_deserialize()` overrides |
| `lib/contracts/view_context.py` | **New** — `ViewContext` dataclass with `from_props()` |
| `lib/ui/layouts/base_view.py` | Add `self.ctx = ViewContext.from_props(props)` |
| `lib/api/routes/auth.py` | Make `login` async; add `await asyncio.sleep(0.5)` on 401 |
| `tests/test_repository_base.py` | Add 9 hook tests |
| `tests/test_base_view.py` | Add 5 ViewContext tests |
| `tests/test_auth_api.py` | Add 2 timing tests |
| `tests/test_smoke.py` | Add `lib.contracts.view_context` import |

---

## Task 1: `_serialize` and `_deserialize` hooks on `AbstractRepository`

**Files:**
- Modify: `lib/repositories/base.py`
- Test: `tests/test_repository_base.py`

The `Pet` / `PetRepository` test fixture already in `test_repository_base.py` is the right vehicle. `Pet` has only scalar columns, so it exercises the base hook behaviour cleanly.

- [ ] **Step 1: Write the failing tests**

Add these tests at the bottom of `tests/test_repository_base.py`:

```python
# ── _serialize() ──────────────────────────────────────────────────────────────

def test_serialize_returns_scalar_columns_as_dict(repo):
    pet = repo.create({"name": "Suki", "species": "cat"})
    result = repo._serialize(pet)
    assert result == {"id": pet.id, "name": "Suki", "species": "cat"}


def test_serialize_subclass_can_add_extra_fields(repo):
    class ExtendedRepo(PetRepository):
        def _serialize(self, obj):
            d = super()._serialize(obj)
            d["display"] = f"{obj.name} ({obj.species})"
            return d

    extended = ExtendedRepo(repo._factory)
    pet = extended.create({"name": "Mochi", "species": "cat"})
    result = extended._serialize(pet)
    assert result["display"] == "Mochi (cat)"


def test_paginate_items_use_serialize_hook(repo):
    class ExtendedRepo(PetRepository):
        def _serialize(self, obj):
            d = super()._serialize(obj)
            d["tag"] = "tagged"
            return d

    extended = ExtendedRepo(repo._factory)
    extended.create({"name": "A", "species": "dog"})
    result = extended.paginate(page=1, page_size=10)
    assert result["items"][0]["tag"] == "tagged"


def test_filter_by_items_use_serialize_hook(repo):
    class ExtendedRepo(PetRepository):
        def _serialize(self, obj):
            d = super()._serialize(obj)
            d["tag"] = "tagged"
            return d

    extended = ExtendedRepo(repo._factory)
    extended.create({"name": "B", "species": "dog"})
    results = extended.filter_by(species="dog")
    assert results[0]["tag"] == "tagged"


# ── _deserialize() ────────────────────────────────────────────────────────────

def test_deserialize_strips_unknown_keys(repo):
    result = repo._deserialize({"name": "Rex", "species": "dog", "unknown": "ignored"})
    assert "unknown" not in result
    assert result == {"name": "Rex", "species": "dog"}


def test_deserialize_keeps_known_keys(repo):
    result = repo._deserialize({"name": "Rex", "species": "dog"})
    assert result == {"name": "Rex", "species": "dog"}


def test_create_ignores_unknown_fields_via_deserialize(repo):
    # Would raise TypeError without _deserialize stripping "junk"
    pet = repo.create({"name": "Lucky", "species": "hamster", "junk": "ignored"})
    assert pet.name == "Lucky"


def test_update_ignores_unknown_fields_via_deserialize(repo):
    pet = repo.create({"name": "Paws", "species": "cat"})
    updated = repo.update(pet.id, {"name": "Paws II", "nonexistent": "value"})
    assert updated.name == "Paws II"


def test_deserialize_subclass_can_coerce_types(repo):
    class CoercingRepo(PetRepository):
        def _deserialize(self, data: dict) -> dict:
            d = super()._deserialize(data)
            if "id" in d and isinstance(d["id"], str):
                d["id"] = int(d["id"])
            return d

    coercing = CoercingRepo(repo._factory)
    result = coercing._deserialize({"id": "42", "name": "X", "species": "y"})
    assert result["id"] == 42
    assert isinstance(result["id"], int)
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_repository_base.py -k "serialize or deserialize" -v
```

Expected: 9 failures — `AttributeError: 'PetRepository' object has no attribute '_serialize'` etc.

- [ ] **Step 3: Implement the hooks in `lib/repositories/base.py`**

Replace the entire file with:

```python
from typing import TypeVar, Generic
from sqlalchemy import inspect as sa_inspect
from lib.core.interfaces import IRepository
from lib.database.session import SessionFactory

T = TypeVar("T")

_FILTER_OPS = frozenset({"like", "gte", "lte", "gt", "lt", "in", "ne"})


class AbstractRepository(IRepository, Generic[T]):
    model: type[T]

    def __init__(self, factory: SessionFactory):
        self._factory = factory

    # ── Serialization hooks ───────────────────────────────────────────────────

    def _serialize(self, obj: T) -> dict:
        """Outbound: ORM object → dict. Override to add relationship fields."""
        return {c.key: getattr(obj, c.key)
                for c in sa_inspect(obj).mapper.column_attrs}

    def _deserialize(self, data: dict) -> dict:
        """Inbound: strip unknown keys. Override to add type coercion on top."""
        known = {c.key for c in sa_inspect(self.model).mapper.column_attrs}
        return {k: v for k, v in data.items() if k in known}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def get(self, id) -> T | None:
        with self._factory.session() as s:
            return s.get(self.model, id)

    def list(self, **filters) -> list[T]:
        with self._factory.session() as s:
            q = s.query(self.model)
            for k, v in filters.items():
                q = q.filter(getattr(self.model, k) == v)
            return q.all()

    def create(self, data: dict) -> T:
        with self._factory.session() as s:
            obj = self.model(**self._deserialize(data))
            s.add(obj)
            s.flush()
            return obj

    def update(self, id, data: dict) -> T | None:
        with self._factory.session() as s:
            obj = s.get(self.model, id)
            if obj is None:
                return None
            for k, v in self._deserialize(data).items():
                setattr(obj, k, v)
            s.flush()
            return obj

    def delete(self, id) -> bool:
        with self._factory.session() as s:
            obj = s.get(self.model, id)
            if obj is None:
                return False
            s.delete(obj)
            return True

    def paginate(self, page: int = 1, page_size: int = 20, **filters) -> dict:
        with self._factory.session() as s:
            q = s.query(self.model)
            for k, v in filters.items():
                q = q.filter(getattr(self.model, k) == v)
            total = q.count()
            rows = q.offset((page - 1) * page_size).limit(page_size).all()
            items = [self._serialize(r) for r in rows]
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": max(1, (total + page_size - 1) // page_size),
            }

    def filter_by(self, **specs) -> list:
        """Query with Django-style lookup operators.

        Supported suffixes (after __):
            like  — SQL LIKE pattern  (e.g. username__like="ali%")
            gte   — >=               (e.g. created_at__gte=some_date)
            lte   — <=
            gt    — >
            lt    — <
            in    — IN list          (e.g. status__in=["active", "pending"])
            ne    — !=

        Plain kwargs remain exact-match (e.g. username="alice").

        Raises ValueError for unknown operators.
        """
        with self._factory.session() as s:
            q = s.query(self.model)
            for spec, value in specs.items():
                if "__" in spec:
                    field_name, _, op = spec.rpartition("__")
                    if op not in _FILTER_OPS:
                        raise ValueError(
                            f"Unknown filter operator {op!r}. "
                            f"Use one of: {', '.join(sorted(_FILTER_OPS))}"
                        )
                    col = getattr(self.model, field_name)
                    if op == "like":
                        q = q.filter(col.like(value))
                    elif op == "gte":
                        q = q.filter(col >= value)
                    elif op == "lte":
                        q = q.filter(col <= value)
                    elif op == "gt":
                        q = q.filter(col > value)
                    elif op == "lt":
                        q = q.filter(col < value)
                    elif op == "in":
                        q = q.filter(col.in_(value))
                    elif op == "ne":
                        q = q.filter(col != value)
                else:
                    q = q.filter(getattr(self.model, spec) == value)
            return [self._serialize(r) for r in q.all()]
```

- [ ] **Step 4: Run all tests**

```bash
pytest --tb=short -q
```

Expected: all 434 existing tests pass + 9 new tests pass = 443 total.

- [ ] **Step 5: Commit**

```bash
git add lib/repositories/base.py tests/test_repository_base.py
git commit -m "feat: add _serialize/_deserialize hooks to AbstractRepository"
```

---

## Task 2: Migrate `UserRepository` to use the hooks

**Files:**
- Modify: `lib/repositories/user_repository.py`
- Verify: `tests/test_repositories.py` (existing tests must still pass — no new tests needed here)

The existing `tests/test_repositories.py` already covers `paginate()` with roles. It will verify the migration is correct.

- [ ] **Step 1: Replace `lib/repositories/user_repository.py`**

```python
import uuid

from lib.repositories.base import AbstractRepository
from lib.models.user import User
from lib.models.role import Role


class UserRepository(AbstractRepository[User]):
    model = User

    def _serialize(self, obj) -> dict:
        d = super()._serialize(obj)
        d["roles"] = [r.name for r in obj.roles]
        return d

    def _deserialize(self, data: dict) -> dict:
        d = super()._deserialize(data)
        for field in ("id", "user_id"):
            if field in d and isinstance(d[field], str):
                d[field] = uuid.UUID(d[field])
        return d

    def add_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        """Add a role to a user. Returns True if added, False if user/role not found or already assigned."""
        with self._factory.session() as s:
            user = s.get(self.model, user_id)
            role = s.get(Role, role_id)
            if not (user and role):
                return False
            if role not in user.roles:
                user.roles.append(role)
                return True
            return False

    def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        """Remove a role from a user. Returns True if removed, False if user not found or role wasn't assigned."""
        with self._factory.session() as s:
            user = s.get(self.model, user_id)
            if not user:
                return False
            before_count = len(user.roles)
            user.roles = [r for r in user.roles if r.id != role_id]
            return len(user.roles) < before_count

    def find_for_auth(self, login: str) -> dict | None:
        """Find user by username or email, return dict for auth (no detached ORM objects)."""
        with self._factory.session() as s:
            user = s.query(User).filter(User.username == login).first()
            if user is None:
                user = s.query(User).filter(User.email == login).first()
            if user is None:
                return None
            return {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "password_hash": user.password_hash,
                "roles": [r.name for r in user.roles],
            }

    def list_by_role(self, role_name: str) -> list[User]:
        """List all users with a specific role."""
        with self._factory.session() as s:
            return s.query(self.model).join(Role, self.model.roles).filter(Role.name == role_name).all()
```

- [ ] **Step 2: Run all tests**

```bash
pytest --tb=short -q
```

Expected: 443 tests pass (same count — no new tests, just verifying nothing regressed).

- [ ] **Step 3: Commit**

```bash
git add lib/repositories/user_repository.py
git commit -m "refactor: UserRepository uses _serialize/_deserialize hooks"
```

---

## Task 3: `ViewContext` dataclass and `BaseView` wiring

**Files:**
- Create: `lib/contracts/view_context.py`
- Modify: `lib/ui/layouts/base_view.py`
- Modify: `tests/test_base_view.py`
- Modify: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing tests**

Add these tests at the bottom of `tests/test_base_view.py`:

```python
# ── ViewContext ────────────────────────────────────────────────────────────

def test_base_view_exposes_ctx(nav_service):
    from lib.contracts.view_context import ViewContext
    v = make_view(HelloView, nav_service=nav_service)
    assert hasattr(v, "ctx")
    assert isinstance(v.ctx, ViewContext)


def test_ctx_nav_service_matches_props(nav_service):
    v = make_view(HelloView, nav_service=nav_service)
    assert v.ctx.nav_service is nav_service


def test_ctx_backend_is_none_when_not_in_props(nav_service):
    v = make_view(HelloView, nav_service=nav_service)
    assert v.ctx.backend is None


def test_ctx_backend_matches_props_when_provided(nav_service):
    page = FakePage("/")
    sentinel = object()
    props = {"nav_service": nav_service, "backend": sentinel}
    from lib.ui.layouts.base_view import BaseView

    class _V(BaseView):
        def build_content(self):
            return ft.Text("x")

    v = _V(page, props)
    assert v.ctx.backend is sentinel


def test_existing_props_dict_still_accessible(nav_service):
    v = make_view(HelloView, nav_service=nav_service)
    assert v.props["nav_service"] is nav_service
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_base_view.py -k "ctx" -v
```

Expected: 5 failures — `AttributeError: 'HelloView' object has no attribute 'ctx'`.

- [ ] **Step 3: Create `lib/contracts/view_context.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ViewContext:
    """Typed view of the props dict injected into every BaseView.

    Fields use Any until Phase 5B fills in real types (importing concrete
    adapter/service types here would create circular dependencies).

    Usage in views:
        self.ctx.backend       # IBackendAdapter | None
        self.ctx.nav_service   # NavigationService
        self.ctx.vault         # Vault | None
        self.ctx.events        # EventBus | None
        self.ctx.dev_nav       # bool
        self.ctx.params        # dict — path params
        self.ctx.query         # dict — query string params
    """

    nav_service: Any
    backend:     Any = None
    nav:         Any = None
    vault:       Any = None
    events:      Any = None
    dev_nav:     bool = False
    params:      dict = field(default_factory=dict)
    query:       dict = field(default_factory=dict)

    @classmethod
    def from_props(cls, props: dict) -> "ViewContext":
        return cls(
            nav_service = props["nav_service"],
            backend     = props.get("backend"),
            nav         = props.get("nav"),
            vault       = props.get("vault"),
            events      = props.get("events"),
            dev_nav     = bool(props.get("dev_nav")),
            params      = props.get("params", {}),
            query       = props.get("query", {}),
        )
```

- [ ] **Step 4: Wire `ViewContext` into `lib/ui/layouts/base_view.py`**

Add the import at the top (after the existing imports):

```python
from lib.contracts.view_context import ViewContext
```

Add one line at the end of `BaseView.__init__`, after the existing `self.params = self._build_params()` line:

```python
self.ctx = ViewContext.from_props(props)
```

The full updated `__init__` looks like:

```python
def __init__(self, page: ft.Page, props: dict):
    self.page = page
    self.props = props
    nav = props.get("nav_service")
    if nav is None:
        raise KeyError(
            f"{type(self).__name__}: props['nav_service'] is required. "
            "Add it to router.set_props_factory()."
        )
    self.nav_service = nav
    self.nav    = props.get("nav")
    self.vault  = props.get("vault")
    self.events = props.get("events")
    self.params = self._build_params()
    self.ctx    = ViewContext.from_props(props)
```

- [ ] **Step 5: Add `lib.contracts.view_context` to smoke test imports**

In `tests/test_smoke.py`, add `"lib.contracts.view_context"` to the `module_path` list. Place it after `"lib.contracts.base"`:

```python
"lib.contracts.base",
"lib.contracts.view_context",   # ← add this line
```

- [ ] **Step 6: Run all tests**

```bash
pytest --tb=short -q
```

Expected: 448 tests pass (443 + 5 new ViewContext tests).

- [ ] **Step 7: Commit**

```bash
git add lib/contracts/view_context.py lib/ui/layouts/base_view.py tests/test_base_view.py tests/test_smoke.py
git commit -m "feat: add ViewContext typed dataclass to BaseView"
```

---

## Task 4: Auth login brute-force delay

**Files:**
- Modify: `lib/api/routes/auth.py`
- Modify: `tests/test_auth_api.py`

- [ ] **Step 1: Write the failing timing tests**

Add these tests at the bottom of `tests/test_auth_api.py`:

```python
import time


def test_failed_login_takes_at_least_400ms(auth_client):
    client, factory = auth_client
    _create_user(factory, "delayuser", "delay@test.com", "correct")
    start = time.monotonic()
    response = client.post("/auth/login", data={"username": "delayuser", "password": "wrong"})
    elapsed = time.monotonic() - start
    assert response.status_code == 401
    assert elapsed >= 0.4, f"Expected >= 0.4s delay on failure, got {elapsed:.3f}s"


def test_successful_login_is_not_delayed(auth_client):
    client, factory = auth_client
    _create_user(factory, "fastuser", "fast@test.com", "correct")
    start = time.monotonic()
    response = client.post("/auth/login", data={"username": "fastuser", "password": "correct"})
    elapsed = time.monotonic() - start
    assert response.status_code == 200
    assert elapsed < 1.0, f"Successful login too slow: {elapsed:.3f}s"
```

- [ ] **Step 2: Run the tests to confirm the delay test fails**

```bash
pytest tests/test_auth_api.py::test_failed_login_takes_at_least_400ms -v
```

Expected: FAIL — elapsed will be < 0.1s (no delay yet).

- [ ] **Step 3: Update `lib/api/routes/auth.py`**

```python
"""
Authentication endpoints — OAuth2 password flow.

POST /auth/login accepts application/x-www-form-urlencoded with `username` and
`password` fields (OAuth2PasswordRequestForm). Returning a Bearer JWT keeps the
API compatible with any OAuth2-aware client and allows swapping in an external
provider later without changing callers.
"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.user_service import UserService
from lib.auth.jwt_handler import create_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_service() -> UserService:
    return UserService(ConnectionRegistry.get())


@router.post("/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(_get_service),
):
    """Authenticate with username/email + password (OAuth2 password flow). Returns Bearer JWT."""
    result = service.execute(ActionRequest(
        action="authenticate",
        data={"username": form.username, "password": form.password},
    ))
    if not result.success:
        await asyncio.sleep(0.5)
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_token({"sub": result.data["id"], "roles": result.data["roles"]})
    return {"access_token": token, "token_type": "bearer"}
```

- [ ] **Step 4: Run all tests**

```bash
pytest --tb=short -q
```

Expected: 450 tests pass (448 + 2 new timing tests).

- [ ] **Step 5: Commit**

```bash
git add lib/api/routes/auth.py tests/test_auth_api.py
git commit -m "feat: add 500ms delay on failed login to slow brute-force"
```

---

## Done — verify the full suite one final time

```bash
pytest --tb=short -q
```

Expected output:
```
450 passed in Xs
```

If anything is red, do not proceed. Fix it before declaring Phase 5A complete.
