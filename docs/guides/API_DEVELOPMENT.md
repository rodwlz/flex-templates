# API Development Guide

How to build HTTP endpoints in FlexTemplates — validation, error handling, testing,
and the common CRUD patterns used throughout the codebase.

**Prerequisites:** Read [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md) first. Every route
calls `service.execute(ActionRequest(...))` and reads an `ActionResult`. If you
understand that contract, the rest of this guide is just mechanics.

**Related docs:**
- [CONVENTIONS.md](CONVENTIONS.md) — naming rules, import rules, module layout
- [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md) — `ActionRequest` / `ActionResult` / `Event`
- [ANTI_PATTERNS.md](ANTI_PATTERNS.md) — what not to do and why
- [API_PATTERN_TEMPLATE.md](API_PATTERN_TEMPLATE.md) — step-by-step walkthrough for adding a new entity

---

## Quick Example

A complete POST endpoint with validation, a service call, and error handling — all
in one place. This is the canonical shape every endpoint in the codebase follows.

### The route

```python
# lib/api/routes/roles.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


def get_service() -> RoleService:
    return RoleService(ConnectionRegistry.get())


@router.post("")
def create_role(data: dict, service: RoleService = Depends(get_service)):
    """Create a role immediately."""
    result = service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

### The test

```python
# tests/test_roles_api.py
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


def _shared_memory_factory() -> SessionFactory:
    factory = SessionFactory.__new__(SessionFactory)
    factory._engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory._Session = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False,
        bind=factory._engine
    )
    return factory


@pytest.fixture
def api_client(monkeypatch):
    factory = _shared_memory_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    app = FastAPI()
    app.include_router(roles_routes.router)
    app.include_router(users_routes.router)
    return TestClient(app)


def test_create_role_returns_id_and_name(api_client):
    response = api_client.post("/roles", json={"name": "admin", "description": "Admin"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "admin"
    assert "id" in data
```

### What the three pieces do

| Piece | Job |
|---|---|
| `ActionRequest(action="create", data=data)` | Carries the verb and payload to the service |
| `result.success` | `True` = the service did its job; `False` = something went wrong |
| `raise HTTPException(...)` | Turns `result.error` into a 4xx HTTP response |

That's the complete pattern. Everything else in this guide expands on one of these three pieces.

---

## Request Validation

### Using Pydantic models for typed request bodies

The route receives `data: dict` by default. When a body has required fields or type
constraints, define a Pydantic model as the body type instead. FastAPI validates it
before the handler runs — no boilerplate needed.

```python
# lib/api/routes/products.py
from pydantic import BaseModel, Field


class CreateProductBody(BaseModel):
    name: str
    price: float = Field(gt=0, description="Must be positive")
    description: str | None = None


@router.post("")
def create_product(
    body: CreateProductBody,
    service: ProductService = Depends(get_service),
):
    result = service.execute(ActionRequest(action="create", data=body.model_dump()))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

If `price` is missing or negative, FastAPI returns a 422 Unprocessable Entity
automatically — the handler never runs. The `data: dict` form is fine when you
trust the caller to send the right shape; use a model when you want a contract
enforced at the HTTP boundary.

### Validating body fields with constraints

Use Pydantic's `Field` validators for simple constraints, and `@field_validator` for
anything involving logic:

```python
from pydantic import BaseModel, Field, field_validator


class CreateUserBody(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def email_must_have_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("not a valid email address")
        return v.lower()


@router.post("")
def create_user(body: CreateUserBody, service: UserService = Depends(get_service)):
    result = service.execute(ActionRequest(action="create", data=body.model_dump()))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

Pydantic validators check **shape and type**. They should not call the database or
enforce business rules. See [CONTRACTS_GUIDE.md — Common mistakes](CONTRACTS_GUIDE.md)
for the distinction between shape validation and business validation.

### Returning validation errors from the service

When the service catches a business-rule violation, it sets `result.success = False`
and populates `result.error`. The route translates that to the right HTTP status:

```python
@router.post("")
def create_role(data: dict, service: RoleService = Depends(get_service)):
    result = service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        # result.error carries the message from the service exception
        raise HTTPException(400, detail=result.error)
    return result.data
```

The service raises, `SimpleService` catches, wraps into `ActionResult(success=False,
error=str(exc))`. The route reads `result.error` and puts it in the HTTP detail.
The caller receives:

```json
{
  "detail": "Role 'admin' already exists"
}
```

No try/except in the route itself — the contract does that job.

---

## Error Handling

### Service exceptions become ActionResult errors

`SimpleService` and `StagingService` catch all exceptions from action methods and
return `ActionResult(success=False, error=str(exc))`. Route handlers never need to
catch exceptions from `service.execute()`:

```python
# lib/services/role_service.py  — raises ValueError on missing entity
def get(self, data: dict) -> dict:
    repo = RoleRepository(self._factory)
    role = repo.get(uuid.UUID(data["id"]))
    if role is None:
        raise ValueError(f"Role {data['id']} not found")   # caught by SimpleService
    return {"id": str(role.id), "name": role.name, "description": role.description}


# lib/api/routes/roles.py  — reads result.success, never catches
@router.get("/{role_id}")
def get_role(role_id: str, service: RoleService = Depends(get_service)):
    result = service.execute(ActionRequest(action="get", data={"id": role_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data
```

Raise in the service, read `result.success` in the route. This is the only pattern
used in this codebase.

### Mapping errors to HTTP status codes

| Condition | Status | When to use |
|---|---|---|
| Missing resource (by ID) | 404 | `"Role X not found"`, `"User X not found"` |
| Invalid input / constraint violation | 400 | Bad field value, duplicate key, missing required field |
| Pydantic body validation failure | 422 | Automatic from FastAPI — no code needed |

```python
# GET / DELETE — resource not found → 404
@router.get("/{user_id}")
def get_user(user_id: str, service: UserService = Depends(get_service)):
    result = service.execute(ActionRequest(action="get", data={"id": user_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data


# POST — creation failure (e.g. duplicate) → 400
@router.post("")
def create_user(data: dict, service: UserService = Depends(get_service)):
    result = service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


# DELETE — not found → 404
@router.delete("/{user_id}")
def delete_user(user_id: str, service: UserService = Depends(get_service)):
    result = service.execute(ActionRequest(action="delete", data={"id": user_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data
```

The rule of thumb: if the caller asked for something that does not exist, return
404; if the caller sent something the service cannot process, return 400.

### When the service is not responsible for the error

For errors that happen before the service runs — a missing query parameter, a
registered resource not found in a registry — raise `HTTPException` directly:

```python
# lib/api/routes/caches.py
from lib.services.cache_registry import CacheRegistry

def _get_or_404(name: str):
    try:
        return CacheRegistry.get(name)
    except RuntimeError:
        raise HTTPException(404, detail=f"Cache adapter {name!r} not registered")

@router.get("/{name}")
def get_cache_status(name: str) -> dict:
    _get_or_404(name)
    result = _tester.execute(ActionRequest(action="test", data={"name": name}))
    return result.model_dump()
```

The registry check happens before the service call. `CacheRegistry.get()` raises
`RuntimeError` when the name is unknown — the `_get_or_404` helper converts that to
a 404. If the name is unknown there is nothing for the service to do, so skip it
and raise immediately.

---

## Testing Endpoints

### Setting up the in-memory test database

All API tests use a `TestClient` backed by an in-memory SQLite database. The setup
helper creates a `SessionFactory` with a `StaticPool` (one shared connection — required
so the schema creator and the route handler use the same in-memory database):

```python
# Pattern used in tests/test_api.py and tests/test_api_routes.py

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.api.routes import roles as roles_routes
from lib.api.routes import users as users_routes
from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base


def _shared_memory_factory() -> SessionFactory:
    factory = SessionFactory.__new__(SessionFactory)
    factory._engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory._Session = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False,
        bind=factory._engine,
    )
    return factory


@pytest.fixture
def api_client(monkeypatch):
    factory = _shared_memory_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    app = FastAPI()
    app.include_router(roles_routes.router)
    app.include_router(users_routes.router)
    return TestClient(app)
```

`monkeypatch.setattr` replaces the real `ConnectionRegistry._factories` for the
duration of the test. Route handlers call `ConnectionRegistry.get()`, which now
returns the test factory. No mocking of service methods required.

### Testing happy paths

```python
def test_post_role_creates_role(api_client):
    """POST /roles creates a role and returns it."""
    response = api_client.post("/roles", json={
        "name": "admin",
        "description": "Administrator",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "admin"
    assert data["description"] == "Administrator"
    assert "id" in data


def test_list_roles_returns_all(api_client):
    """GET /roles returns every created role."""
    api_client.post("/roles", json={"name": "admin", "description": "Admin"})
    api_client.post("/roles", json={"name": "editor", "description": "Editor"})

    response = api_client.get("/roles")
    assert response.status_code == 200
    assert len(response.json()["roles"]) == 2


def test_get_user_includes_roles_array(api_client):
    """GET /users/{id} returns the user with a roles field."""
    create_resp = api_client.post("/users", json={
        "username": "bob",
        "email": "bob@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })
    user_id = create_resp.json()["id"]

    response = api_client.get(f"/users/{user_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "bob"
    assert "roles" in body
    assert body["roles"] == []
```

### Testing error paths (404s and 400s)

Always test the failure path. The error message shape matters to clients.

```python
def test_get_role_404_when_missing(api_client):
    """GET /roles/{id} with an unknown UUID returns 404."""
    import uuid
    response = api_client.get(f"/roles/{uuid.uuid4()}")
    assert response.status_code == 404


def test_delete_role_404_when_missing(api_client):
    """DELETE /roles/{id} returns 404 for a UUID that does not exist."""
    import uuid
    response = api_client.delete(f"/roles/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_user_404_on_malformed_uuid(api_client):
    """A non-UUID path segment surfaces as 404.

    The route parameter is typed `str`. The service calls `uuid.UUID(data['id'])`,
    which raises ValueError on a malformed string. SimpleService wraps that as
    ActionResult(success=False), and the route returns 404.
    """
    response = api_client.get("/users/not-a-uuid")
    assert response.status_code == 404


def test_get_user_404_detail_contains_id(api_client):
    """The 404 detail string includes the missing ID so the caller knows what went wrong."""
    import uuid
    missing_id = str(uuid.uuid4())
    response = api_client.get(f"/users/{missing_id}")
    assert response.status_code == 404
    assert missing_id in response.json()["detail"]
```

### Testing validation failures

```python
def test_create_user_400_on_missing_username(api_client):
    """POST /users without a username returns 400 (the service raises ValueError)."""
    response = api_client.post("/users", json={
        "email": "no-username@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })
    # Missing username causes a KeyError in the service, wrapped as success=False
    assert response.status_code == 400


def test_create_product_422_on_invalid_price(api_client):
    """When the route uses a Pydantic body model, bad input returns 422 before the
    handler runs. This tests the FastAPI validation layer, not the service."""
    response = api_client.post("/products", json={
        "name": "Widget",
        "price": -5.00,  # Field(gt=0) rejects negative prices
    })
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("price" in str(e) for e in errors)
```

---

## Response Shaping

### When to return data directly vs wrapping it

Routes always call `result.data` — never `result.model_dump()` unless the caller
needs the full `ActionResult` envelope including `success`, `events`, and `error`.

```python
# CORRECT — return just the data dict
@router.get("/{role_id}")
def get_role(role_id: str, service: RoleService = Depends(get_service)):
    result = service.execute(ActionRequest(action="get", data={"id": role_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data   # {"id": "...", "name": "admin", "description": "..."}


# WHEN model_dump IS appropriate — diagnostic / status endpoints
# lib/api/routes/caches.py
@router.get("/{name}")
def get_cache_status(name: str) -> dict:
    _get_or_404(name)   # raises 404 if not registered; see _get_or_404 helper above
    result = _tester.execute(ActionRequest(action="test", data={"name": name}))
    return result.model_dump()   # {"success": true, "data": {...}, "events": [], "error": null}
```

Diagnostic endpoints (health checks, test probes) reasonably return the full
`ActionResult` shape. CRUD endpoints return `result.data` only.

### What goes in the response dict

Services translate ORM objects to plain dicts before returning. UUID fields become
strings. Relationships are expanded inline if the consumer needs them, omitted if not.

```python
# lib/services/user_service.py  — full user response
def get(self, data: dict) -> dict:
    repo = UserRepository(self._factory)
    user = repo.get(uuid.UUID(data["id"]))
    if user is None:
        raise ValueError(f"User {data['id']} not found")
    return {
        "id": str(user.id),          # UUID → str
        "username": user.username,
        "email": user.email,
        "roles": [                    # relationship expanded inline
            {"id": str(r.id), "name": r.name}
            for r in user.roles
        ],
    }


# lib/services/user_service.py  — list response (fewer fields, faster)
def list(self, data: dict) -> dict:
    repo = UserRepository(self._factory)
    users = repo.list()
    return {
        "users": [
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "role_count": len(u.roles),  # count, not the full list
            }
            for u in users
        ]
    }
```

The list endpoint returns `role_count` instead of expanding each role — the consumer
can call `GET /users/{id}` to fetch the full detail. This is a deliberate tradeoff
between payload size and round-trips.

### Serializing ORM objects safely

ORM objects must be serialized **inside** the session context. Accessing a lazy
relationship after the session closes raises `DetachedInstanceError`. The correct
pattern is to read every field you need inside `with factory.session() as s:` and
return a plain dict.

```python
# CORRECT — serialize inside the session, inside the repository
# Illustrative pattern: UserRepository doesn't have get_with_roles(), but shows how to use session correctly
class UserRepository(AbstractRepository[User]):
    model = User

    def get_with_roles(self, id) -> dict | None:
        with self._factory.session() as s:
            user = s.get(self.model, id)
            if not user:
                return None
            # All ORM access happens here, before the context manager exits
            return {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "roles": [
                    {"id": str(r.id), "name": r.name}
                    for r in user.roles        # safe — session still open
                ],
            }


# WRONG — accessing relationships after the session closes
def get_with_roles_broken(self, id) -> User | None:
    with self._factory.session() as s:
        return s.get(self.model, id)          # session closes here

# Later in the service:
user = repo.get_with_roles_broken(some_id)
roles = user.roles                            # DetachedInstanceError
```

For the full guidance on session management, see
[ANTI_PATTERNS.md — Anti-Pattern 7](ANTI_PATTERNS.md).

---

## Common Patterns

### Full CRUD — immediate operations

The four CRUD endpoints follow a fixed structure. The role routes are the canonical
reference:

```python
# lib/api/routes/roles.py  — complete CRUD example
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


def get_service() -> RoleService:
    return RoleService(ConnectionRegistry.get())


@router.post("")
def create_role(data: dict, service: RoleService = Depends(get_service)):
    result = service.execute(ActionRequest(action="create", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.get("")
def list_roles(service: RoleService = Depends(get_service)):
    result = service.execute(ActionRequest(action="list", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.get("/{role_id}")
def get_role(role_id: str, service: RoleService = Depends(get_service)):
    result = service.execute(ActionRequest(action="get", data={"id": role_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data


@router.delete("/{role_id}")
def delete_role(role_id: str, service: RoleService = Depends(get_service)):
    result = service.execute(ActionRequest(action="delete", data={"id": role_id}))
    if not result.success:
        raise HTTPException(404, detail=result.error)
    return result.data
```

**GET and DELETE use 404.** POST uses 400. This is the consistent pattern across
all route files — check [lib/api/routes/users.py](../lib/api/routes/users.py) and
[lib/api/routes/roles.py](../lib/api/routes/roles.py) for the live examples.

### Filtering and pagination via query parameters

Pass query parameters through `ActionRequest.data` by collecting them in the handler
signature. FastAPI parses them from the URL automatically:

```python
@router.get("")
def list_users(
    skip: int = 0,
    limit: int = 10,
    service: UserService = Depends(get_service),
):
    """GET /users?skip=0&limit=10"""
    result = service.execute(ActionRequest(
        action="list",
        data={"skip": skip, "limit": limit},
    ))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

The service method reads `data["skip"]` and `data["limit"]` and passes them to the
repository:

```python
# Example pattern for adding pagination — UserService.list() doesn't yet support skip/limit.
# To implement: add skip/limit parameters to UserService.list() and AbstractRepository.list()
# lib/services/user_service.py
def list(self, data: dict) -> dict:
    repo = UserRepository(self._factory)
    users = repo.list(
        skip=data.get("skip", 0),
        limit=data.get("limit", 10),
    )
    return {
        "users": [
            {"id": str(u.id), "username": u.username, "email": u.email}
            for u in users
        ]
    }
```

For filtering by a field value, add the filter as a query parameter and pass it
the same way:

```python
@router.get("")
def list_products(
    status: str | None = None,
    tag: str | None = None,
    limit: int = 50,
    service: ProductService = Depends(get_service),
):
    """GET /products?status=active&tag=sale&limit=20"""
    result = service.execute(ActionRequest(
        action="list",
        data={"status": status, "tag": tag, "limit": limit},
    ))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

### Staged and approval-required operations

Some operations are too complex or risky to commit in one step. The framework
provides two multi-step patterns:

**Staged (preview → confirm or cancel):**

```python
# lib/api/routes/users.py  — staged user creation with roles

# The service carries open unit-of-work between stage and confirm.
# Cache one instance per factory so both calls hit the same object.
# Note: For multi-worker deployments, use a database or Redis-backed store instead of module-level dicts.
# This pattern is safe for development/single-process deployments.
_service_cache: dict[int, UserService] = {}


def get_service() -> UserService:
    factory = ConnectionRegistry.get()
    key = id(factory)
    if key not in _service_cache:
        _service_cache[key] = UserService(factory)
    return _service_cache[key]


@router.post("/with-roles/stage")
def stage_user_with_roles(data: dict, service: UserService = Depends(get_service)):
    """Stage creation — returns a preview diff. Nothing is committed yet."""
    result = service.execute(ActionRequest(action="stage", data=data))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data   # {"preview": {"new": [...], "modified": [...], "deleted": []}, ...}


@router.post("/with-roles/confirm")
def confirm_user_with_roles(service: UserService = Depends(get_service)):
    """Commit the staged operation."""
    result = service.execute(ActionRequest(action="confirm", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.post("/with-roles/cancel")
def cancel_user_with_roles(service: UserService = Depends(get_service)):
    """Roll back the staged operation."""
    result = service.execute(ActionRequest(action="cancel", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

**Approval-required (same shape, different signal):**

Use `requires_approval=True` on the `ActionRequest` to tell clients that an
explicit second step is mandatory before commit. The flag does not change service
behavior on its own — the service or a policy layer enforces it:

```python
@router.post("/bulk-delete/request")
def request_bulk_delete(data: dict, service: UserService = Depends(get_service)):
    """Stage a bulk delete. Requires explicit approval before it commits."""
    result = service.execute(
        ActionRequest(action="stage", data=data, requires_approval=True)
    )
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data


@router.post("/bulk-delete/approve")
def approve_bulk_delete(data: dict, service: UserService = Depends(get_service)):
    """Approve and commit the staged bulk delete."""
    result = service.execute(ActionRequest(action="confirm", data={}))
    if not result.success:
        raise HTTPException(400, detail=result.error)
    return result.data
```

**Testing the staged flow:**

```python
def test_stage_user_with_roles(api_client):
    """stage returns preview; confirm commits."""
    role_resp = api_client.post("/roles", json={"name": "admin", "description": "Admin"})
    role_id = role_resp.json()["id"]

    stage_resp = api_client.post("/users/with-roles/stage", json={
        "username": "charlie",
        "email": "charlie@example.com",
        "password_hash": "hash",
        "salt": "salt",
        "role_ids": [role_id],
    })
    assert stage_resp.status_code == 200
    assert "preview" in stage_resp.json()

    confirm_resp = api_client.post("/users/with-roles/confirm")
    assert confirm_resp.status_code == 200

    users_resp = api_client.get("/users")
    assert any(u["username"] == "charlie" for u in users_resp.json()["users"])


def test_cancel_staged_user_does_not_persist(api_client):
    """stage followed by cancel leaves the database unchanged."""
    api_client.post("/users/with-roles/stage", json={
        "username": "dave",
        "email": "dave@example.com",
        "password_hash": "hash",
        "salt": "salt",
        "role_ids": [],
    })

    cancel_resp = api_client.post("/users/with-roles/cancel")
    assert cancel_resp.status_code == 200

    users_resp = api_client.get("/users")
    assert not any(u["username"] == "dave" for u in users_resp.json()["users"])


def test_approval_required_request_then_approve(api_client):
    """approval flow: request stages, approve commits."""
    request_resp = api_client.post("/users/bulk-delete/request", json={
        "username": "frank",
        "email": "frank@example.com",
        "password_hash": "hash",
        "salt": "salt",
        "role_ids": [],
    })
    assert request_resp.status_code == 200
    assert "preview" in request_resp.json()

    approve_resp = api_client.post("/users/bulk-delete/approve", json={})
    assert approve_resp.status_code == 200
    assert approve_resp.json()["confirmed"] is True
```

---

## Three Operation Types at a Glance

| Type | When to use | HTTP shape | Service base |
|---|---|---|---|
| Immediate | Simple CRUD, no preview needed | `POST/GET/DELETE /entity` | `SimpleService` |
| Staged | Multi-step with relationships, user needs a diff before committing | `POST /entity/stage`, `POST /entity/confirm`, `POST /entity/cancel` | `StagingService` |
| Approval | High-risk or irreversible — explicit second confirmation required | `POST /entity/action/request`, `POST /entity/action/approve` | `StagingService` with `requires_approval=True` |

---

## Auto-Discovery

Drop a route file in `lib/api/routes/` with a module-level `router` variable and
`mount_routes()` picks it up automatically on startup:

```python
# lib/api/router_registry.py  — nothing to change when adding new routes
import importlib
import pkgutil
from fastapi import FastAPI


def mount_routes(app: FastAPI, package: str = "lib.api.routes") -> None:
    mod = importlib.import_module(package)
    for _, name, _ in pkgutil.iter_modules(mod.__path__):
        sub = importlib.import_module(f"{package}.{name}")
        if hasattr(sub, "router"):
            app.include_router(sub.router)
```

No registration, no list to update. Verify: start the server and open
`http://localhost:8080/docs` — your new routes appear under their tag automatically.

---

## Checklist Before Merging a New Endpoint

- [ ] Route file is in `lib/api/routes/` and defines `router = APIRouter(...)`
- [ ] `get_service()` calls `ConnectionRegistry.get()` — no `SessionFactory()` inline
- [ ] `HTTPException(404)` for missing resources, `HTTPException(400)` for bad input
- [ ] No try/except around `service.execute()` — the contract handles that
- [ ] Tests cover: happy path, 404 on unknown ID, 400 on bad input
- [ ] Services raise exceptions with clear messages (the message becomes `result.error`)
- [ ] ORM objects serialized to dicts inside the session context, not outside

For the full entity checklist (model → repository → service → route → tests),
see [API_PATTERN_TEMPLATE.md — Testing Checklist](API_PATTERN_TEMPLATE.md).
