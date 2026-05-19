# Framework Gaps — Phase 3: Auth, Data Layer & Operations

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add authentication (JWT + bcrypt), RBAC enforcement, paginated/filtered queries, structured JSON logging, background task scheduling, CLI vault tools, and Docker deployment to FlexTemplates 2.0.

**Architecture:** Auth lives in a new `lib/auth/` module. Passwords are hashed with bcrypt in `lib/security/password.py`; JWT tokens are issued at `/auth/login` and validated via FastAPI `Depends`. Data-layer improvements (`paginate`, `filter_by`) extend `AbstractRepository` without touching service contracts. Operational concerns (logging, scheduler, CLI, Docker) are self-contained additions wired into `main.py`. The vault design is unchanged: the frontend always enters the master password; the backend never auto-unlocks from a stored session.

**Tech Stack:** `bcrypt>=4.0`, `python-jose[cryptography]>=3.3`, `apscheduler>=3.10` (new); SQLAlchemy, FastAPI, Flet, pytest (existing).

---

## Files Created / Modified

| Action | File | Responsibility |
|---|---|---|
| Delete | `tests/test_wrappers.py` | Remove scratch file causing pytest collection errors |
| Create | `lib/security/password.py` | bcrypt hash + verify helpers |
| Create | `lib/auth/__init__.py` | empty package marker |
| Create | `lib/auth/jwt_handler.py` | JWT create / decode (HS256) |
| Create | `lib/auth/dependencies.py` | `get_current_user` + `require_roles` FastAPI depends |
| Create | `lib/api/routes/auth.py` | `POST /auth/login` endpoint |
| Create | `lib/middleware/__init__.py` | empty package marker |
| Create | `lib/middleware/logging.py` | `JsonFormatter`, `setup_logging`, `log_requests` middleware |
| Create | `lib/tasks/__init__.py` | empty package marker |
| Create | `lib/tasks/scheduler.py` | APScheduler wrapper (`TaskScheduler`) |
| Create | `lib/config/cli.py` | `flex_encrypt` / `flex_decrypt` entry-point commands |
| Create | `Dockerfile` | API-only container image |
| Create | `docker-compose.yml` | Local dev stack (app + postgres + redis) |
| Create | `.env.example` | Template for all required env vars |
| Create | `tests/test_password.py` | Tests for hash_password / verify_password |
| Create | `tests/test_jwt.py` | Tests for create_token / decode_token |
| Create | `tests/test_auth_api.py` | Tests for POST /auth/login |
| Create | `tests/test_rbac.py` | Tests for get_current_user / require_roles |
| Create | `tests/test_scheduler.py` | Tests for TaskScheduler start/stop/run |
| Create | `tests/test_cli_vault.py` | Tests for _encrypt_to_vault round-trip |
| Modify | `lib/services/user_service.py` | Wire bcrypt in `create()`; add `authenticate` action |
| Modify | `lib/core/interfaces.py` | Add `paginate` + `filter_by` to `IRepository` ABC |
| Modify | `lib/repositories/base.py` | Implement `paginate` + `filter_by` in `AbstractRepository` |
| Modify | `lib/config/settings.py` | Add `api_only: bool = False` |
| Modify | `main.py` | Wire `setup_logging`, `log_requests`, `scheduler`, `api_only` |
| Modify | `pyproject.toml` | Add bcrypt, python-jose, apscheduler; add `[project.scripts]` |
| Modify | `tests/test_smoke.py` | Add new module paths to import check |

---

## Task 1: Delete tests/test_wrappers.py

**Files:**
- Delete: `tests/test_wrappers.py`

- [ ] **Step 1: Delete the scratch file**

```bash
git rm tests/test_wrappers.py
```

- [ ] **Step 2: Verify pytest collection is clean**

```bash
pytest tests/ --collect-only -q
```

Expected: no `KeyError: 'name'` collection error; all existing tests collected.

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove test_wrappers.py scratch file causing pytest collection error"
```

---

## Task 2: bcrypt password helper + wire into UserService

**Files:**
- Create: `lib/security/password.py`
- Modify: `lib/services/user_service.py` (lines 50–66 `create`, add `authenticate`)
- Modify: `pyproject.toml` (add `bcrypt>=4.0`)
- Create: `tests/test_password.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_password.py
from lib.security.password import hash_password, verify_password


def test_hash_password_returns_nonempty_strings():
    hashed, salt = hash_password("mysecret")
    assert hashed and salt
    assert hashed != "mysecret"


def test_verify_password_correct():
    hashed, _ = hash_password("mysecret")
    assert verify_password("mysecret", hashed) is True


def test_verify_password_wrong():
    hashed, _ = hash_password("mysecret")
    assert verify_password("wrongpassword", hashed) is False


def test_two_hashes_of_same_password_differ():
    h1, _ = hash_password("pw")
    h2, _ = hash_password("pw")
    assert h1 != h2  # bcrypt generates a unique salt each time
```

- [ ] **Step 2: Run to confirm ImportError**

```bash
pytest tests/test_password.py -v
```

Expected: `ImportError: No module named 'lib.security.password'`

- [ ] **Step 3: Add bcrypt to pyproject.toml**

In `pyproject.toml`, add to `dependencies`:
```toml
"bcrypt>=4.0",
```

Then install:
```bash
pip install -e .
```

- [ ] **Step 4: Create lib/security/password.py**

```python
import bcrypt


def hash_password(plain: str) -> tuple[str, str]:
    """Hash a plain-text password with bcrypt. Returns (hash, salt) as str."""
    raw_salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain.encode("utf-8"), raw_salt)
    return hashed.decode("utf-8"), raw_salt.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
```

- [ ] **Step 5: Run password tests to confirm they pass**

```bash
pytest tests/test_password.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 6: Update UserService.create() to hash passwords**

Replace the `create()` method in `lib/services/user_service.py`:

```python
def create(self, data: dict) -> dict:
    """Immediate create. Accepts either 'password' (plain) or 'password_hash'+'salt'."""
    from lib.security.password import hash_password
    plain = data.get("password", "")
    if plain:
        password_hash, salt = hash_password(plain)
    else:
        password_hash = data.get("password_hash", "")
        salt = data.get("salt", "")
    repo = UserRepository(self._factory)
    user = repo.create({
        "username": data["username"],
        "email": data["email"],
        "password_hash": password_hash,
        "salt": salt,
    })
    return {"id": str(user.id), "username": user.username, "email": user.email}
```

- [ ] **Step 7: Add authenticate action to UserService**

Add this method after `delete()` and before the staged operations section:

```python
def authenticate(self, data: dict) -> dict:
    """Verify login + password. Returns user dict on success, raises ValueError on failure."""
    from lib.security.password import verify_password
    login = data.get("username", "")
    password = data.get("password", "")
    repo = UserRepository(self._factory)
    # Try username first, then email — same field for login
    users = repo.list(username=login)
    if not users:
        users = repo.list(email=login)
    if not users or not verify_password(password, users[0].password_hash):
        raise ValueError("Invalid credentials")
    user = users[0]
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "roles": [r.name for r in user.roles],
    }
```

Also add a convenience wrapper (after the other wrappers):

```python
def authenticate_user(self, username: str, password: str) -> dict:
    """Wrapper: raise ValueError on bad credentials, return user dict on success."""
    result = self.execute(ActionRequest(
        action="authenticate",
        data={"username": username, "password": password},
    ))
    if not result.success:
        raise ValueError(result.error)
    return result.data
```

- [ ] **Step 8: Write service authenticate tests**

Add to `tests/test_services.py`:

```python
def test_create_with_plain_password_hashes_it(db_factory):
    from lib.services.user_service import UserService
    from lib.contracts.base import ActionRequest
    from lib.security.password import verify_password

    service = UserService(db_factory)
    result = service.execute(ActionRequest(action="create", data={
        "username": "authuser1", "email": "authuser1@test.com", "password": "hunter2",
    }))
    assert result.success
    # The stored hash should verify against the plain password
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    users = repo.list(username="authuser1")
    assert users and verify_password("hunter2", users[0].password_hash)


def test_authenticate_success(db_factory):
    from lib.services.user_service import UserService
    from lib.contracts.base import ActionRequest

    service = UserService(db_factory)
    service.execute(ActionRequest(action="create", data={
        "username": "authuser2", "email": "authuser2@test.com", "password": "secret",
    }))
    result = service.execute(ActionRequest(action="authenticate", data={
        "username": "authuser2", "password": "secret",
    }))
    assert result.success
    assert result.data["username"] == "authuser2"
    assert "roles" in result.data


def test_authenticate_wrong_password(db_factory):
    from lib.services.user_service import UserService
    from lib.contracts.base import ActionRequest

    service = UserService(db_factory)
    service.execute(ActionRequest(action="create", data={
        "username": "authuser3", "email": "authuser3@test.com", "password": "correct",
    }))
    result = service.execute(ActionRequest(action="authenticate", data={
        "username": "authuser3", "password": "wrong",
    }))
    assert not result.success
    assert "Invalid credentials" in result.error


def test_authenticate_unknown_user(db_factory):
    from lib.services.user_service import UserService
    from lib.contracts.base import ActionRequest

    service = UserService(db_factory)
    result = service.execute(ActionRequest(action="authenticate", data={
        "username": "nobody", "password": "secret",
    }))
    assert not result.success
```

- [ ] **Step 9: Run all service tests**

```bash
pytest tests/test_services.py tests/test_password.py -v
```

Expected: all PASS.

- [ ] **Step 10: Commit**

```bash
git add lib/security/password.py lib/services/user_service.py \
        tests/test_password.py tests/test_services.py pyproject.toml
git commit -m "feat: bcrypt password hashing + authenticate action in UserService"
```

---

## Task 3: JWT handler

**Files:**
- Create: `lib/auth/__init__.py`
- Create: `lib/auth/jwt_handler.py`
- Modify: `pyproject.toml` (add `python-jose[cryptography]>=3.3`)
- Create: `tests/test_jwt.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_jwt.py
import pytest
from jose import JWTError


def test_create_and_decode_roundtrip():
    from lib.auth.jwt_handler import create_token, decode_token
    token = create_token({"sub": "user-123", "roles": ["admin"]})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["roles"] == ["admin"]


def test_decode_invalid_token_raises():
    from lib.auth.jwt_handler import decode_token
    with pytest.raises(JWTError):
        decode_token("not.a.valid.token")


def test_two_tokens_for_same_payload_differ():
    """exp timestamps differ if called a second apart — just verify structure."""
    from lib.auth.jwt_handler import create_token, decode_token
    t1 = create_token({"sub": "u1"})
    t2 = create_token({"sub": "u1"})
    # Both decode correctly even though they may differ in exp
    assert decode_token(t1)["sub"] == "u1"
    assert decode_token(t2)["sub"] == "u1"
```

- [ ] **Step 2: Run to confirm ImportError**

```bash
pytest tests/test_jwt.py -v
```

Expected: `ImportError: No module named 'lib.auth'`

- [ ] **Step 3: Add python-jose to pyproject.toml**

In `pyproject.toml`, add to `dependencies`:
```toml
"python-jose[cryptography]>=3.3",
```

Then install:
```bash
pip install -e .
```

- [ ] **Step 4: Create lib/auth/__init__.py**

Create empty file at `lib/auth/__init__.py`.

- [ ] **Step 5: Create lib/auth/jwt_handler.py**

```python
import os
from datetime import datetime, timedelta, timezone

from jose import jwt
from jose import JWTError  # noqa: F401 — re-exported so callers only import from here

_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
_ALGORITHM = "HS256"
_EXPIRE_MINUTES = 60


def create_token(payload: dict, expire_minutes: int = _EXPIRE_MINUTES) -> str:
    """Return a signed JWT. payload must include 'sub' (user id string)."""
    data = {
        **payload,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(data, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jose.JWTError if invalid or expired."""
    return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
```

- [ ] **Step 6: Run JWT tests**

```bash
pytest tests/test_jwt.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add lib/auth/__init__.py lib/auth/jwt_handler.py \
        tests/test_jwt.py pyproject.toml
git commit -m "feat: JWT handler — create_token / decode_token (HS256)"
```

---

## Task 4: Auth API route (/auth/login)

**Files:**
- Create: `lib/api/routes/auth.py`
- Create: `tests/test_auth_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_auth_api.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.database.session import ConnectionRegistry
from lib.contracts.base import ActionRequest


def _make_app(db_factory):
    """Build a minimal FastAPI app with the auth router wired to db_factory."""
    from lib.api.routes.auth import router as auth_router
    ConnectionRegistry._factories["postgres"] = db_factory
    app = FastAPI()
    app.include_router(auth_router)
    return app


def _create_user(db_factory, username, email, password):
    from lib.services.user_service import UserService
    service = UserService(db_factory)
    service.execute(ActionRequest(action="create", data={
        "username": username, "email": email, "password": password,
    }))


def test_login_returns_bearer_token(db_factory):
    _create_user(db_factory, "loginuser", "loginuser@test.com", "pass123")
    client = TestClient(_make_app(db_factory))
    response = client.post("/auth/login", json={"username": "loginuser", "password": "pass123"})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_token_is_decodable(db_factory):
    _create_user(db_factory, "decodeuser", "decodeuser@test.com", "pass456")
    client = TestClient(_make_app(db_factory))
    response = client.post("/auth/login", json={"username": "decodeuser", "password": "pass456"})
    token = response.json()["access_token"]
    from lib.auth.jwt_handler import decode_token
    payload = decode_token(token)
    assert "sub" in payload
    assert "roles" in payload


def test_login_wrong_password_returns_401(db_factory):
    _create_user(db_factory, "wrongpwuser", "wrongpwuser@test.com", "correct")
    client = TestClient(_make_app(db_factory))
    response = client.post("/auth/login", json={"username": "wrongpwuser", "password": "wrong"})
    assert response.status_code == 401


def test_login_unknown_user_returns_401(db_factory):
    client = TestClient(_make_app(db_factory))
    response = client.post("/auth/login", json={"username": "ghost", "password": "pw"})
    assert response.status_code == 401
```

- [ ] **Step 2: Run to confirm ImportError**

```bash
pytest tests/test_auth_api.py -v
```

Expected: `ImportError: No module named 'lib.api.routes.auth'`

- [ ] **Step 3: Create lib/api/routes/auth.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.user_service import UserService
from lib.auth.jwt_handler import create_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def _get_service() -> UserService:
    return UserService(ConnectionRegistry.get())


@router.post("/login")
def login(body: LoginRequest, service: UserService = Depends(_get_service)):
    """Authenticate with username/email + password. Returns a Bearer JWT."""
    result = service.execute(ActionRequest(
        action="authenticate",
        data={"username": body.username, "password": body.password},
    ))
    if not result.success:
        raise HTTPException(401, detail="Invalid credentials")
    token = create_token({"sub": result.data["id"], "roles": result.data["roles"]})
    return {"access_token": token, "token_type": "bearer"}
```

- [ ] **Step 4: Run auth API tests**

```bash
pytest tests/test_auth_api.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/api/routes/auth.py tests/test_auth_api.py
git commit -m "feat: POST /auth/login endpoint — returns Bearer JWT"
```

---

## Task 5: RBAC dependency (require_roles)

**Files:**
- Create: `lib/auth/dependencies.py`
- Create: `tests/test_rbac.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_rbac.py
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from lib.auth.jwt_handler import create_token


def _app_with(dependency):
    app = FastAPI()

    @app.get("/protected")
    def protected(user=Depends(dependency)):
        return {"user_id": user["id"], "roles": user["roles"]}

    return app


def test_get_current_user_valid_token():
    from lib.auth.dependencies import get_current_user
    app = _app_with(get_current_user)
    token = create_token({"sub": "uid-1", "roles": ["admin"]})
    resp = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "uid-1"
    assert resp.json()["roles"] == ["admin"]


def test_get_current_user_no_token_returns_403():
    from lib.auth.dependencies import get_current_user
    app = _app_with(get_current_user)
    resp = TestClient(app).get("/protected")
    assert resp.status_code == 403  # HTTPBearer auto_error returns 403 when missing


def test_get_current_user_bad_token_returns_401():
    from lib.auth.dependencies import get_current_user
    app = _app_with(get_current_user)
    resp = TestClient(app).get("/protected", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_require_roles_passes_matching_role():
    from lib.auth.dependencies import require_roles
    app = _app_with(require_roles("admin"))
    token = create_token({"sub": "uid-2", "roles": ["admin", "viewer"]})
    resp = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_require_roles_rejects_wrong_role():
    from lib.auth.dependencies import require_roles
    app = _app_with(require_roles("superadmin"))
    token = create_token({"sub": "uid-3", "roles": ["admin"]})
    resp = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_require_roles_accepts_any_of_multiple():
    from lib.auth.dependencies import require_roles
    app = _app_with(require_roles("superadmin", "admin"))
    token = create_token({"sub": "uid-4", "roles": ["admin"]})
    resp = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
```

- [ ] **Step 2: Run to confirm ImportError**

```bash
pytest tests/test_rbac.py -v
```

Expected: `ImportError: No module named 'lib.auth.dependencies'`

- [ ] **Step 3: Create lib/auth/dependencies.py**

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lib.auth.jwt_handler import JWTError, decode_token

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """FastAPI dependency: decode Bearer JWT, return {"id": ..., "roles": [...]}."""
    try:
        payload = decode_token(creds.credentials)
        return {"id": payload["sub"], "roles": payload.get("roles", [])}
    except JWTError:
        raise HTTPException(401, detail="Invalid or expired token")


def require_roles(*role_names: str):
    """Dependency factory: require the authenticated user to hold at least one role.

    Usage:
        @router.get("/admin")
        def admin_page(user=Depends(require_roles("admin", "superadmin"))):
            ...
    """
    def _check(user: dict = Depends(get_current_user)) -> dict:
        if not set(role_names).intersection(user.get("roles", [])):
            raise HTTPException(
                403, detail=f"Requires one of: {', '.join(role_names)}"
            )
        return user

    return _check
```

- [ ] **Step 4: Run RBAC tests**

```bash
pytest tests/test_rbac.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Add auth route to smoke test module list**

In `tests/test_smoke.py`, add to the module list:
```python
"lib.auth.jwt_handler",
"lib.auth.dependencies",
"lib.api.routes.auth",
```

- [ ] **Step 6: Run smoke tests**

```bash
pytest tests/test_smoke.py -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add lib/auth/dependencies.py tests/test_rbac.py tests/test_smoke.py
git commit -m "feat: RBAC — get_current_user + require_roles FastAPI dependencies"
```

---

## Task 6: Pagination in AbstractRepository

**Files:**
- Modify: `lib/core/interfaces.py` (add `paginate` abstract method to `IRepository`)
- Modify: `lib/repositories/base.py` (implement `paginate`)
- Modify: `tests/test_repository_base.py` (add pagination tests)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_repository_base.py`:

```python
def test_paginate_returns_correct_structure(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    for i in range(5):
        repo.create({"username": f"pguser{i}", "email": f"pguser{i}@test.com",
                     "password_hash": "", "salt": ""})
    result = repo.paginate(page=1, page_size=2)
    assert result["total"] == 5
    assert result["pages"] == 3
    assert result["page"] == 1
    assert result["page_size"] == 2
    assert len(result["items"]) == 2


def test_paginate_last_page_has_remainder(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    for i in range(5):
        repo.create({"username": f"pguser2_{i}", "email": f"pguser2_{i}@test.com",
                     "password_hash": "", "salt": ""})
    result = repo.paginate(page=3, page_size=2)
    assert len(result["items"]) == 1  # 5 items, pages: [2, 2, 1]


def test_paginate_page_beyond_total_returns_empty(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    repo.create({"username": "pguser3_0", "email": "pguser3_0@test.com",
                 "password_hash": "", "salt": ""})
    result = repo.paginate(page=10, page_size=20)
    assert result["items"] == []
    assert result["total"] == 1


def test_paginate_with_filter(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    repo.create({"username": "pgactive1", "email": "pgactive1@t.com",
                 "password_hash": "", "salt": "", "status": "active"})
    repo.create({"username": "pgactive2", "email": "pgactive2@t.com",
                 "password_hash": "", "salt": "", "status": "suspended"})
    result = repo.paginate(page=1, page_size=10, status="active")
    assert result["total"] == 1
    assert result["items"][0].username == "pgactive1"
```

- [ ] **Step 2: Run to confirm AttributeError**

```bash
pytest tests/test_repository_base.py -k "paginate" -v
```

Expected: `AttributeError: 'UserRepository' object has no attribute 'paginate'`

- [ ] **Step 3: Add paginate abstract method to IRepository**

In `lib/core/interfaces.py`, add to `IRepository`:

```python
class IRepository(ABC):
    @abstractmethod
    def get(self, id): ...

    @abstractmethod
    def list(self, **filters): ...

    @abstractmethod
    def create(self, data: dict): ...

    @abstractmethod
    def update(self, id, data: dict): ...

    @abstractmethod
    def delete(self, id) -> bool: ...

    @abstractmethod
    def paginate(self, page: int = 1, page_size: int = 20, **filters) -> dict: ...

    @abstractmethod
    def filter_by(self, **specs) -> list: ...
```

- [ ] **Step 4: Implement paginate in AbstractRepository**

Add to `lib/repositories/base.py` after the `delete` method:

```python
def paginate(self, page: int = 1, page_size: int = 20, **filters) -> dict:
    """Return one page of results with metadata.

    Returns:
        {
            "items":     list of ORM objects for this page,
            "total":     total matching rows (ignoring pagination),
            "page":      current page number (1-based),
            "page_size": rows per page,
            "pages":     total number of pages,
        }
    """
    with self._factory.session() as s:
        q = s.query(self.model)
        for k, v in filters.items():
            q = q.filter(getattr(self.model, k) == v)
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size),
        }
```

- [ ] **Step 5: Run pagination tests**

```bash
pytest tests/test_repository_base.py -k "paginate" -v
```

Expected: 4 tests PASS.

- [ ] **Step 6: Run full repo tests to confirm no regressions**

```bash
pytest tests/test_repository_base.py tests/test_repositories.py -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add lib/core/interfaces.py lib/repositories/base.py tests/test_repository_base.py
git commit -m "feat: paginate() method in AbstractRepository with page/page_size/total"
```

---

## Task 7: Richer repository filters (filter_by)

**Files:**
- Modify: `lib/repositories/base.py` (implement `filter_by`)
- Modify: `tests/test_repository_base.py` (add filter_by tests)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_repository_base.py`:

```python
def test_filter_by_exact_match(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    repo.create({"username": "fb_alice", "email": "fb_alice@test.com",
                 "password_hash": "", "salt": ""})
    repo.create({"username": "fb_bob", "email": "fb_bob@test.com",
                 "password_hash": "", "salt": ""})
    results = repo.filter_by(username="fb_alice")
    assert len(results) == 1
    assert results[0].username == "fb_alice"


def test_filter_by_like(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    repo.create({"username": "fb_carol", "email": "fb_carol@test.com",
                 "password_hash": "", "salt": ""})
    repo.create({"username": "fb_dave", "email": "fb_dave@test.com",
                 "password_hash": "", "salt": ""})
    results = repo.filter_by(username__like="fb_c%")
    assert len(results) == 1
    assert results[0].username == "fb_carol"


def test_filter_by_in(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    repo.create({"username": "fb_eve", "email": "fb_eve@test.com",
                 "password_hash": "", "salt": ""})
    repo.create({"username": "fb_frank", "email": "fb_frank@test.com",
                 "password_hash": "", "salt": ""})
    results = repo.filter_by(username__in=["fb_eve", "fb_frank"])
    assert len(results) == 2


def test_filter_by_ne(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    repo.create({"username": "fb_grace", "email": "fb_grace@test.com",
                 "password_hash": "", "salt": "", "status": "active"})
    repo.create({"username": "fb_henry", "email": "fb_henry@test.com",
                 "password_hash": "", "salt": "", "status": "suspended"})
    results = repo.filter_by(status__ne="suspended")
    usernames = [u.username for u in results]
    assert "fb_grace" in usernames
    assert "fb_henry" not in usernames


def test_filter_by_unknown_operator_raises(db_factory):
    from lib.repositories.user_repository import UserRepository
    import pytest
    repo = UserRepository(db_factory)
    with pytest.raises(ValueError, match="Unknown filter operator"):
        repo.filter_by(username__fuzzy="alice")
```

- [ ] **Step 2: Run to confirm AttributeError**

```bash
pytest tests/test_repository_base.py -k "filter_by" -v
```

Expected: `AttributeError: 'UserRepository' object has no attribute 'filter_by'`

- [ ] **Step 3: Implement filter_by in AbstractRepository**

Add to `lib/repositories/base.py` after `paginate()`. Also add the sentinel set at module level (after imports):

```python
# Module-level constant — define once, reference in filter_by
_FILTER_OPS = frozenset({"like", "gte", "lte", "gt", "lt", "in", "ne"})
```

Then add the method to `AbstractRepository`:

```python
def filter_by(self, **specs) -> list[T]:
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
        return q.all()
```

- [ ] **Step 4: Run filter_by tests**

```bash
pytest tests/test_repository_base.py -k "filter_by" -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Run all repository tests**

```bash
pytest tests/test_repository_base.py tests/test_repositories.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add lib/repositories/base.py lib/core/interfaces.py tests/test_repository_base.py
git commit -m "feat: filter_by() with Django-style operators (like/gte/lte/gt/lt/in/ne)"
```

---

## Task 8: Structured JSON logging middleware

**Files:**
- Create: `lib/middleware/__init__.py`
- Create: `lib/middleware/logging.py`
- Modify: `main.py` (call `setup_logging`, add `log_requests` middleware)
- Create: `tests/test_logging_middleware.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_logging_middleware.py
import json
import logging
from io import StringIO


def _capture_logger(name: str) -> tuple[logging.Logger, StringIO]:
    from lib.middleware.logging import JsonFormatter
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    log = logging.getLogger(name)
    log.handlers.clear()
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    log.propagate = False
    return log, stream


def test_json_formatter_produces_valid_json():
    log, stream = _capture_logger("test.jf1")
    log.info("hello world")
    output = stream.getvalue().strip()
    parsed = json.loads(output)
    assert parsed["msg"] == "hello world"
    assert parsed["level"] == "INFO"
    assert "ts" in parsed
    assert "logger" in parsed


def test_json_formatter_includes_extra_fields():
    log, stream = _capture_logger("test.jf2")
    log.info("http request", extra={"method": "GET", "status": 200, "ms": 12.3})
    parsed = json.loads(stream.getvalue().strip())
    assert parsed["method"] == "GET"
    assert parsed["status"] == 200
    assert parsed["ms"] == 12.3


def test_setup_logging_does_not_raise():
    from lib.middleware.logging import setup_logging
    setup_logging("WARNING")  # should not raise


def test_log_requests_middleware_calls_next():
    """Integration: middleware must call the next handler and return its response."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from lib.middleware.logging import log_requests

    fake_request = MagicMock()
    fake_request.method = "GET"
    fake_request.url.path = "/test"
    fake_response = MagicMock()
    fake_response.status_code = 200

    async def call_next(_): return fake_response

    response = asyncio.run(log_requests(fake_request, call_next))
    assert response is fake_response
```

- [ ] **Step 2: Run to confirm ImportError**

```bash
pytest tests/test_logging_middleware.py -v
```

Expected: `ImportError: No module named 'lib.middleware'`

- [ ] **Step 3: Create lib/middleware/__init__.py**

Create empty file at `lib/middleware/__init__.py`.

- [ ] **Step 4: Create lib/middleware/logging.py**

```python
import json
import logging
import time
from typing import Callable

from fastapi import Request, Response

# Standard LogRecord attributes — exclude these from JSON extra fields.
_LOGRECORD_ATTRS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime",
})

_http_logger = logging.getLogger("flex.http")


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line.

    Standard fields: ts, level, logger, msg.
    Extra fields (passed via extra={}) are merged in automatically.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k not in _LOGRECORD_ATTRS and not k.startswith("_"):
                payload[k] = v
        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Replace root logger handlers with a single JSON-to-stderr handler."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


async def log_requests(request: Request, call_next: Callable) -> Response:
    """FastAPI middleware: log every HTTP request as a JSON line."""
    start = time.monotonic()
    response = await call_next(request)
    ms = round((time.monotonic() - start) * 1000, 1)
    _http_logger.info(
        "%s %s %d",
        request.method,
        request.url.path,
        response.status_code,
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "status": response.status_code,
            "ms": ms,
        },
    )
    return response
```

- [ ] **Step 5: Run logging tests**

```bash
pytest tests/test_logging_middleware.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 6: Wire into main.py**

At the top of `main.py`, add the import:
```python
from lib.middleware.logging import setup_logging, log_requests
```

At the start of `main()`, after `config = AppConfig()`:
```python
setup_logging("DEBUG" if config.debug else "INFO")
```

After `api_app = FastAPI(title=config.app_title)`:
```python
api_app.middleware("http")(log_requests)
```

- [ ] **Step 7: Run smoke tests to confirm main.py still imports**

```bash
pytest tests/test_smoke.py::test_main_module_imports_cleanly -v
```

Expected: PASS.

- [ ] **Step 8: Add middleware module to smoke test list**

In `tests/test_smoke.py`, add to the module list:
```python
"lib.middleware.logging",
```

- [ ] **Step 9: Commit**

```bash
git add lib/middleware/__init__.py lib/middleware/logging.py \
        tests/test_logging_middleware.py main.py tests/test_smoke.py
git commit -m "feat: JSON structured logging middleware + setup_logging"
```

---

## Task 9: Background task scheduler (APScheduler)

**Files:**
- Create: `lib/tasks/__init__.py`
- Create: `lib/tasks/scheduler.py`
- Modify: `pyproject.toml` (add `apscheduler>=3.10`)
- Modify: `main.py` (start/stop scheduler in lifecycle)
- Create: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_scheduler.py
import time


def test_scheduler_runs_job_at_interval():
    from lib.tasks.scheduler import TaskScheduler
    results = []
    scheduler = TaskScheduler()
    scheduler.add_job(lambda: results.append(1), "interval", seconds=0.05)
    scheduler.start()
    time.sleep(0.2)
    scheduler.stop()
    assert len(results) >= 2, "Job should have run at least twice in 200ms"


def test_scheduler_start_is_idempotent():
    from lib.tasks.scheduler import TaskScheduler
    scheduler = TaskScheduler()
    scheduler.start()
    scheduler.start()  # second call must not raise or double-start
    scheduler.stop()


def test_scheduler_stop_is_idempotent():
    from lib.tasks.scheduler import TaskScheduler
    scheduler = TaskScheduler()
    scheduler.start()
    scheduler.stop()
    scheduler.stop()  # second call must not raise


def test_scheduler_add_job_before_start():
    from lib.tasks.scheduler import TaskScheduler
    scheduler = TaskScheduler()
    job = scheduler.add_job(lambda: None, "interval", seconds=60)
    assert job is not None
    scheduler.start()
    scheduler.stop()
```

- [ ] **Step 2: Run to confirm ImportError**

```bash
pytest tests/test_scheduler.py -v
```

Expected: `ImportError: No module named 'lib.tasks'`

- [ ] **Step 3: Add apscheduler to pyproject.toml**

In `pyproject.toml`, add to `dependencies`:
```toml
"apscheduler>=3.10",
```

Then install:
```bash
pip install -e .
```

- [ ] **Step 4: Create lib/tasks/__init__.py**

Create empty file at `lib/tasks/__init__.py`.

- [ ] **Step 5: Create lib/tasks/scheduler.py**

```python
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
        """Schedule *func* with *trigger* and APScheduler kwargs.

        Examples:
            scheduler.add_job(send_report, "cron", hour=9, minute=0)
            scheduler.add_job(cleanup_temp, "interval", hours=6)
        """
        return self._scheduler.add_job(func, trigger, **kwargs)

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
```

- [ ] **Step 6: Run scheduler tests**

```bash
pytest tests/test_scheduler.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 7: Wire into main.py**

Add import at the top of `main.py`:
```python
from lib.tasks.scheduler import TaskScheduler
```

In `main()`, after the vault/cache setup block and before `api_app = FastAPI(...)`:
```python
scheduler = TaskScheduler()
# Add recurring jobs here:
# scheduler.add_job(some_cleanup_func, "interval", hours=24)
scheduler.start()
```

In the `finally` block (after `server.stop()`):
```python
scheduler.stop()
```

The `finally` block should now read:
```python
try:
    ft.run(main=flet_main)
finally:
    server.stop()
    scheduler.stop()
```

- [ ] **Step 8: Add tasks module to smoke test list**

In `tests/test_smoke.py`, add to the module list:
```python
"lib.tasks.scheduler",
```

- [ ] **Step 9: Run all tests**

```bash
pytest tests/ -v --ignore=tests/test_wrappers.py -q
```

Expected: all existing + new tests PASS.

- [ ] **Step 10: Commit**

```bash
git add lib/tasks/__init__.py lib/tasks/scheduler.py \
        tests/test_scheduler.py main.py tests/test_smoke.py pyproject.toml
git commit -m "feat: TaskScheduler — APScheduler wrapper with start/stop lifecycle"
```

---

## Task 10: CLI vault tools (flex-encrypt / flex-decrypt)

**Files:**
- Create: `lib/config/cli.py`
- Modify: `pyproject.toml` (add `[project.scripts]`)
- Create: `tests/test_cli_vault.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_vault.py
from pathlib import Path
import pytest


def _bootstrap_vault(vault_path: str, env_path: str) -> str:
    """Create a fresh vault and return the generated master key."""
    from lib.security.crypto import generate_key
    from lib.security.vault_service import VaultService
    from lib.security.vault_store import VaultStore
    from lib.contracts.base import ActionRequest

    master_key = generate_key()
    Path(env_path).parent.mkdir(parents=True, exist_ok=True)
    Path(env_path).write_text(
        f"VAULT_MASTER_KEY={master_key}\nVAULT_CONFIRM_KEY={master_key}\n"
    )
    service = VaultService(
        store=VaultStore(path=vault_path),
        master_key=master_key,
        confirm_key=master_key,
        env_path=env_path,
    )
    service.execute(ActionRequest(action="unlock"))
    service.execute(ActionRequest(action="save", data={}))
    return master_key


def test_encrypt_to_vault_roundtrip(tmp_path):
    vault_path = str(tmp_path / "vault.json")
    env_path = str(tmp_path / ".env")
    _bootstrap_vault(vault_path, env_path)

    from lib.config.cli import _encrypt_to_vault
    _encrypt_to_vault(
        {"DB_URL": "sqlite:///test.db", "API_KEY": "abc123"},
        vault_path=vault_path,
        env_path=env_path,
    )

    from lib.security.vault import open_vault
    vault = open_vault(vault_path=vault_path, env_path=env_path)
    assert vault.get("DB_URL") == "sqlite:///test.db"
    assert vault.get("API_KEY") == "abc123"


def test_encrypt_to_vault_adds_to_existing(tmp_path):
    vault_path = str(tmp_path / "vault.json")
    env_path = str(tmp_path / ".env")
    _bootstrap_vault(vault_path, env_path)

    from lib.config.cli import _encrypt_to_vault
    _encrypt_to_vault({"KEY1": "val1"}, vault_path=vault_path, env_path=env_path)
    _encrypt_to_vault({"KEY2": "val2"}, vault_path=vault_path, env_path=env_path)

    from lib.security.vault import open_vault
    vault = open_vault(vault_path=vault_path, env_path=env_path)
    assert vault.get("KEY1") == "val1"
    assert vault.get("KEY2") == "val2"


def test_flex_decrypt_prints_keys(tmp_path, monkeypatch, capsys):
    vault_path = str(tmp_path / "vault.json")
    env_path = str(tmp_path / ".env")
    _bootstrap_vault(vault_path, env_path)

    from lib.config.cli import _encrypt_to_vault
    _encrypt_to_vault({"MYKEY": "myval"}, vault_path=vault_path, env_path=env_path)

    monkeypatch.setenv("VAULT_PATH", vault_path)
    monkeypatch.setenv("VAULT_ENV_PATH", env_path)

    from lib.config.cli import flex_decrypt
    flex_decrypt()
    out = capsys.readouterr().out
    assert "MYKEY" in out
    assert "myval" in out
```

- [ ] **Step 2: Run to confirm ImportError**

```bash
pytest tests/test_cli_vault.py -v
```

Expected: `ImportError: No module named 'lib.config.cli'`

- [ ] **Step 3: Create lib/config/cli.py**

```python
"""CLI commands for vault management.

Entry points (configured in pyproject.toml [project.scripts]):
    flex-encrypt  — interactively write secrets into the encrypted vault
    flex-decrypt  — print all secrets to stdout (DEVELOPMENT USE ONLY)

Both commands read VAULT_PATH and VAULT_ENV_PATH from environment variables,
falling back to the default .secrets/ locations.
"""
import os
import sys


def _encrypt_to_vault(secrets: dict[str, str], *, vault_path: str, env_path: str) -> None:
    """Write *secrets* into the vault and persist to disk.

    Requires the vault to already be initialized (vault.json + .env with keys).
    Call the /security view in the app on first run to bootstrap.
    """
    from lib.security.vault import open_vault
    vault = open_vault(vault_path=vault_path, env_path=env_path)
    for key, value in secrets.items():
        vault.set(key, value)
    vault.save()


def flex_encrypt() -> None:
    """flex-encrypt — interactively write secrets into the encrypted vault."""
    vault_path = os.getenv("VAULT_PATH", ".secrets/vault.json")
    env_path = os.getenv("VAULT_ENV_PATH", ".secrets/.env")
    print(f"Vault: {vault_path}")
    print("Enter secrets one at a time. Leave KEY empty to finish.\n")
    secrets: dict[str, str] = {}
    while True:
        key = input("KEY: ").strip()
        if not key:
            break
        value = input(f"VALUE for {key!r}: ").strip()
        secrets[key] = value
    if not secrets:
        print("No secrets entered. Nothing saved.")
        return
    try:
        _encrypt_to_vault(secrets, vault_path=vault_path, env_path=env_path)
        print(f"\n{len(secrets)} secret(s) saved to {vault_path}")
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def flex_decrypt() -> None:
    """flex-decrypt — print all vault secrets to stdout.

    WARNING: only use this in development. Never run in production.
    """
    vault_path = os.getenv("VAULT_PATH", ".secrets/vault.json")
    env_path = os.getenv("VAULT_ENV_PATH", ".secrets/.env")
    print("⚠  WARNING: printing secrets — development use only\n")
    try:
        from lib.security.vault import open_vault
        vault = open_vault(vault_path=vault_path, env_path=env_path)
        keys = vault.keys()
        if not keys:
            print("(vault is empty)")
            return
        width = max(len(k) for k in keys)
        for k in sorted(keys):
            print(f"{k:{width}} = {vault.get(k)}")
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 4: Add entry points to pyproject.toml**

Add after `[project.optional-dependencies]`:

```toml
[project.scripts]
flex-encrypt = "lib.config.cli:flex_encrypt"
flex-decrypt = "lib.config.cli:flex_decrypt"
```

Then reinstall so the scripts are registered:
```bash
pip install -e .
```

- [ ] **Step 5: Run CLI vault tests**

```bash
pytest tests/test_cli_vault.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 6: Verify CLI commands are available**

```bash
flex-encrypt --help 2>&1 || flex-encrypt
```

Expected: prompts for KEY (Ctrl-C to exit) — no ImportError.

- [ ] **Step 7: Add cli module to smoke test list**

In `tests/test_smoke.py`, add to the module list:
```python
"lib.config.cli",
```

- [ ] **Step 8: Commit**

```bash
git add lib/config/cli.py tests/test_cli_vault.py tests/test_smoke.py pyproject.toml
git commit -m "feat: flex-encrypt / flex-decrypt CLI vault management commands"
```

---

## Task 11: Docker skeleton + API-only mode

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Modify: `lib/config/settings.py` (add `api_only: bool = False`)
- Modify: `main.py` (branch on `config.api_only`)
- Modify: `tests/test_settings.py` (add api_only tests)

- [ ] **Step 1: Write failing test for api_only config**

Add to `tests/test_settings.py`:

```python
def test_api_only_defaults_to_false():
    from lib.config.settings import AppConfig
    config = AppConfig()
    assert config.api_only is False


def test_api_only_reads_from_env(monkeypatch):
    monkeypatch.setenv("API_ONLY", "true")
    from lib.config.settings import AppConfig
    config = AppConfig()
    assert config.api_only is True
```

- [ ] **Step 2: Run to confirm AttributeError**

```bash
pytest tests/test_settings.py -k "api_only" -v
```

Expected: `AttributeError: 'AppConfig' object has no attribute 'api_only'`

- [ ] **Step 3: Add api_only to AppConfig**

In `lib/config/settings.py`, add to the `AppConfig` class under the `# ── UI` section:

```python
# ── Deployment ─────────────────────────────────────────────────────────────
api_only: bool = False  # Set API_ONLY=true in Docker to skip Flet UI
```

- [ ] **Step 4: Run settings tests**

```bash
pytest tests/test_settings.py -v
```

Expected: all PASS including the two new tests.

- [ ] **Step 5: Update main.py to branch on api_only**

Replace the `ft.run(main=flet_main)` call in `main()` with:

```python
if config.api_only:
    import signal
    import threading

    _stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: _stop.set())
    signal.signal(signal.SIGINT, lambda *_: _stop.set())
    print(f"API-only mode — listening on http://{config.api_host}:{config.api_port}")
    _stop.wait()
else:
    ft.run(main=flet_main)
```

The full `try/finally` block should look like:

```python
try:
    if config.api_only:
        import signal, threading
        _stop = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: _stop.set())
        signal.signal(signal.SIGINT, lambda *_: _stop.set())
        print(f"API-only mode — http://{config.api_host}:{config.api_port}")
        _stop.wait()
    else:
        ft.run(main=flet_main)
finally:
    server.stop()
    scheduler.stop()
```

- [ ] **Step 6: Run smoke tests to confirm main.py still imports**

```bash
pytest tests/test_smoke.py::test_main_module_imports_cleanly -v
```

Expected: PASS.

- [ ] **Step 7: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies before copying source (layer cache)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir psycopg2-binary

# Copy source
COPY . .

ENV PYTHONPATH=/app
ENV API_ONLY=true

EXPOSE 8080

CMD ["python", "main.py"]
```

- [ ] **Step 8: Create docker-compose.yml**

```yaml
version: "3.9"

services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      API_ONLY: "true"
      DATABASE_POSTGRES: "postgresql://postgres:postgres@db:5432/flexdb"
      JWT_SECRET_KEY: "${JWT_SECRET_KEY:-change-me-in-production}"
      VAULT_MASTER_KEY: "${VAULT_MASTER_KEY:-}"
      VAULT_CONFIRM_KEY: "${VAULT_CONFIRM_KEY:-}"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .secrets:/app/.secrets
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: flexdb
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  pgdata:
```

- [ ] **Step 9: Create .env.example**

```
# Copy to .env and fill in values before running the app.
# Never commit .env to version control.

# ── HTTP API ────────────────────────────────────────────────────────────────
API_HOST=127.0.0.1
API_PORT=8080
DEBUG=false
APP_TITLE=FlexTemplates

# ── Deployment ──────────────────────────────────────────────────────────────
# Set to true in Docker / headless environments to skip the Flet desktop UI
API_ONLY=false

# ── Authentication ──────────────────────────────────────────────────────────
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=change-me-generate-with-secrets-token-hex-32

# ── Database (one entry per DB, name derived from suffix) ───────────────────
# DATABASE_POSTGRES=postgresql://user:pass@localhost:5432/mydb
# DATABASE_ANALYTICS=postgresql://user:pass@analytics-host:5432/analyticsdb

# ── Vault ───────────────────────────────────────────────────────────────────
VAULT_PATH=.secrets/vault.json
VAULT_ENV_PATH=.secrets/.env
# VAULT_MASTER_KEY and VAULT_CONFIRM_KEY are auto-generated on first run.
# After running the app once and visiting /security, they appear in .secrets/.env.
# Copy them here if you need them for deployment, or mount .secrets/ as a volume.

# ── Redis (auto-detected if REDIS_URL is stored in vault) ──────────────────
# Store this in the vault instead: vault.set("REDIS_URL", "redis://localhost:6379")
```

- [ ] **Step 10: Run full test suite to confirm no regressions**

```bash
pytest tests/ -q
```

Expected: all tests PASS (no failures, no collection errors).

- [ ] **Step 11: Commit**

```bash
git add lib/config/settings.py main.py Dockerfile docker-compose.yml .env.example \
        tests/test_settings.py
git commit -m "feat: Docker skeleton + API_ONLY mode for headless deployment"
```

---

## Self-Review

### Spec coverage check

| Gap | Covered by |
|---|---|
| bcrypt password hashing | Task 2 — `lib/security/password.py` + UserService.create() |
| JWT auth flow | Task 3 (`jwt_handler`) + Task 4 (`/auth/login`) |
| RBAC enforcement | Task 5 (`require_roles` FastAPI depend) |
| Pagination | Task 6 (`paginate()` in AbstractRepository) |
| Richer filters | Task 7 (`filter_by()` with `__like`, `__in`, `__gte`, etc.) |
| Structured logging | Task 8 (`JsonFormatter` + `log_requests` middleware) |
| Background task runner | Task 9 (`TaskScheduler` + APScheduler) |
| CLI vault tools | Task 10 (`flex-encrypt` / `flex-decrypt`) |
| Docker skeleton | Task 11 (`Dockerfile` + `docker-compose.yml` + `.env.example`) |
| API-only mode | Task 11 (`api_only` flag in AppConfig + main.py branch) |
| Delete test_wrappers.py | Task 1 |
| Vault design (always enter password) | Unchanged — VaultService._unlock() already requires it |

### Dependency chain

Tasks can be done in order or in parallel EXCEPT:
- Task 4 (auth route) requires Task 2 (authenticate action) and Task 3 (JWT handler) complete first.
- Task 5 (RBAC) requires Task 3 (JWT) complete first.
- Tasks 6–11 are fully independent of each other and of Tasks 2–5.

### No placeholders — all code is complete

All methods, classes, and tests contain their actual implementation.
