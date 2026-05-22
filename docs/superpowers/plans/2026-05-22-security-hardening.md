# Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close four security gaps in the FlexTemplates FastAPI backend: JWT dev-secret only hard-fails in API_ONLY mode, no CORS policy, no rate limiting on the login endpoint, and auth is opt-in per route.

**Architecture:** A V1 contract router (`lib/api/v1.py`) wraps every `/v1/` route in either a `public` sub-router (login only, login-rate-limit) or a `protected` sub-router (general-rate-limit + Bearer JWT). Route modules lose their `/v1` prefix — the parent `v1_router` owns it. CORS is added as FastAPI middleware in `main.py`. JWT strict mode becomes a testable `_check_jwt_secret` function in `jwt_handler.py` controlled by `AppConfig.jwt_strict`.

**Tech Stack:** FastAPI `APIRouter` dependency injection, `fastapi.middleware.cors.CORSMiddleware`, `pydantic-settings` `AppConfig`, `python-jose` JWT, in-memory sliding-window rate limiter with Redis fallback.

---

## Background for implementers

### Where everything lives

```
lib/api/routes/       ← FastAPI route modules (each exports router = APIRouter(...))
lib/api/v1.py         ← NEW: make_v1_router(config) → (v1_router, public, protected)
lib/api/rate_limiter.py ← NEW: RateLimiter callable class
lib/api/router_registry.py ← auto-discovers routes; mounts through v1 contract
lib/auth/jwt_handler.py    ← HS256 JWT, runs code at module-import time
lib/config/settings.py    ← AppConfig(BaseSettings); reads .secrets/.env
main.py               ← only file that names concrete types; wires everything
```

### Critical constraint — env file location

All env vars (`JWT_SECRET_KEY`, `JWT_STRICT`, `CORS_ORIGINS`, `RATE_LIMIT_*`) live in
`.secrets/.env`. `AppConfig.model_config` currently has `env_file=".env"` (root) — Task 1
changes this to `env_file=".secrets/.env"`. Never use the project-root `.env`.

### Current route prefixes (all have `/v1` today)

```
lib/api/routes/auth.py      prefix="/v1/auth"
lib/api/routes/users.py     prefix="/v1/users"
lib/api/routes/roles.py     prefix="/v1/roles"
lib/api/routes/caches.py    prefix="/v1/caches"
lib/api/routes/scheduler.py prefix="/v1/scheduler"
```

After Task 5, all lose `/v1` from their prefix. The v1_router from `lib/api/v1.py` provides
the prefix for all routes automatically.

### Existing test infrastructure

`tests/conftest.py` has `http_app` (mounts all route routers) and `http_backend`
(HttpBackendAdapter wired to in-memory test DB). Six test files also mount route routers
directly and use `/v1/...` URLs. Task 5 adds `_v1_app(*routers)` to conftest and updates
all six files so URLs stay unchanged after the prefix change.

---

## File Map

| File | Action | What changes |
|---|---|---|
| `lib/config/settings.py` | Modify | Add 4 security fields; change `env_file` to `.secrets/.env` |
| `lib/auth/jwt_handler.py` | Modify | Extract `_check_jwt_secret(key, strict)` function; import AppConfig |
| `lib/api/rate_limiter.py` | Create | `RateLimiter` callable dependency class |
| `lib/api/v1.py` | Create | `make_v1_router(config)` — public + protected sub-routers |
| `lib/api/routes/auth.py` | Modify | Remove `/v1` prefix; add `_PUBLIC_ROUTER = True` |
| `lib/api/routes/users.py` | Modify | Remove `/v1` from prefix |
| `lib/api/routes/roles.py` | Modify | Remove `/v1` from prefix |
| `lib/api/routes/caches.py` | Modify | Remove `/v1` from prefix |
| `lib/api/routes/scheduler.py` | Modify | Remove `/v1` from prefix |
| `lib/api/router_registry.py` | Modify | Accept `config`; mount through v1 sub-routers |
| `main.py` | Modify | Add `CORSMiddleware`; pass `config` to `mount_routes` |
| `tests/conftest.py` | Modify | Add `_v1_app` helper; update `http_app` fixture |
| `tests/test_api.py` | Modify | `api_client` fixture: use `_v1_app` |
| `tests/test_auth_api.py` | Modify | `auth_client` fixture: use `_v1_app` |
| `tests/test_api_routes.py` | Modify | `api_client` fixture: use `_v1_app` |
| `tests/test_api_caches.py` | Modify | `client` fixture: use `_v1_app` |
| `tests/test_api_roles_assign.py` | Modify | `assign_client` fixture: use `_v1_app` |
| `tests/test_auth_me.py` | Modify | `auth_client` fixture: use `_v1_app` |
| `tests/test_settings.py` | Modify | Add 2 tests for new security fields |
| `tests/test_jwt.py` | Modify | Add 3 tests for `_check_jwt_secret` |
| `tests/test_rate_limiter.py` | Create | 4 unit tests for RateLimiter |
| `tests/test_security_contract.py` | Create | 4 structural/behavioral audit tests |
| `tests/test_security_behaviour.py` | Create | 7 runtime auth + rate-limit tests |
| `tests/test_security_cors.py` | Create | 3 CORS header tests |
| `tests/test_smoke.py` | Modify | Add `lib.api.rate_limiter`, `lib.api.v1` imports |

---

## Task 1: AppConfig security fields

**Files:**
- Modify: `lib/config/settings.py`
- Modify: `tests/test_settings.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_settings.py`:

```python
def test_security_field_defaults():
    """New security fields have safe defaults."""
    config = AppConfig()
    assert config.jwt_strict is False
    assert "localhost" in config.cors_origins
    assert config.rate_limit_per_minute > 0
    assert config.rate_limit_login_per_minute > 0
    assert config.rate_limit_login_per_minute <= config.rate_limit_per_minute


def test_jwt_strict_reads_from_env(monkeypatch):
    monkeypatch.setenv("JWT_STRICT", "true")
    config = AppConfig()
    assert config.jwt_strict is True
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_settings.py::test_security_field_defaults tests/test_settings.py::test_jwt_strict_reads_from_env -v
```

Expected: FAIL — `AppConfig` has no `jwt_strict` attribute.

- [ ] **Step 3: Replace `lib/config/settings.py` with the updated version**

```python
"""
AppConfig — single source of truth for app configuration.

Replaces scattered os.getenv() calls. Priority: env vars > .secrets/.env file > defaults.
Security-relevant settings (JWT_SECRET_KEY, CORS_ORIGINS, RATE_LIMIT_*) live in
.secrets/.env alongside vault keys — never in a root .env file.
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    # ── HTTP server ────────────────────────────────────────────────────────────
    api_host: str = "127.0.0.1"
    api_port: int = 8080

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./dev.db"
    primary_database: str = "postgres"
    databases: dict[str, str] = {}

    # ── Vault / secrets ────────────────────────────────────────────────────────
    vault_master_key: str = ""
    vault_confirm_key: str = ""
    vault_path: str = ".secrets/vault.json"
    vault_env_path: str = ".secrets/.env"

    # ── Security ───────────────────────────────────────────────────────────────
    jwt_strict: bool = False                  # hard-fail on dev secret in all modes
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    rate_limit_per_minute: int = 60           # general /v1/ protected routes
    rate_limit_login_per_minute: int = 5      # POST /v1/auth/login

    # ── UI ─────────────────────────────────────────────────────────────────────
    app_title: str = "FlexTemplates"
    debug: bool = False

    # ── Deployment ─────────────────────────────────────────────────────────────
    api_only: bool = False

    model_config = SettingsConfigDict(
        env_file=".secrets/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.databases = self._load_databases_from_env()

    def _load_databases_from_env(self) -> dict[str, str]:
        env: dict[str, str] = dict(os.environ)
        env_file = str(self.model_config.get("env_file", ".secrets/.env"))
        try:
            from dotenv import dotenv_values
            env.update(dotenv_values(env_file))
        except Exception:
            pass

        databases = {}
        prefix = "DATABASE_"
        for key, value in env.items():
            if key.startswith(prefix) and value:
                db_name = key[len(prefix):].lower()
                databases[db_name] = value
        return databases
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_settings.py -v
```

Expected: all test_settings.py tests PASS (existing + 2 new).

- [ ] **Step 5: Run full suite**

```
pytest --tb=short -q
```

Expected: all 518 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add lib/config/settings.py tests/test_settings.py
git commit -m "feat: add security fields to AppConfig; env_file → .secrets/.env"
```

---

## Task 2: JWT strict mode

**Files:**
- Modify: `lib/auth/jwt_handler.py`
- Modify: `tests/test_jwt.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_jwt.py`:

```python
def test_check_jwt_secret_exits_when_strict():
    """_check_jwt_secret(dev_key, strict=True) calls sys.exit(1)."""
    from lib.auth.jwt_handler import _check_jwt_secret, _DEV_SECRET
    with pytest.raises(SystemExit):
        _check_jwt_secret(_DEV_SECRET, strict=True)


def test_check_jwt_secret_warns_when_not_strict():
    """_check_jwt_secret(dev_key, strict=False) emits a UserWarning."""
    import warnings
    from lib.auth.jwt_handler import _check_jwt_secret, _DEV_SECRET
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _check_jwt_secret(_DEV_SECRET, strict=False)
    assert len(w) == 1
    assert "JWT_SECRET_KEY" in str(w[0].message)


def test_check_jwt_secret_silent_for_real_key():
    """_check_jwt_secret does nothing when the key is not the dev default."""
    import warnings
    from lib.auth.jwt_handler import _check_jwt_secret
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _check_jwt_secret("a-real-production-secret", strict=True)
        _check_jwt_secret("a-real-production-secret", strict=False)
    assert len(w) == 0
```

Add `import pytest` at the top of `tests/test_jwt.py` if not already present.

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_jwt.py::test_check_jwt_secret_exits_when_strict tests/test_jwt.py::test_check_jwt_secret_warns_when_not_strict tests/test_jwt.py::test_check_jwt_secret_silent_for_real_key -v
```

Expected: FAIL — `_check_jwt_secret` not defined in `jwt_handler`.

- [ ] **Step 3: Replace `lib/auth/jwt_handler.py`**

```python
import os
import sys
import warnings
from datetime import datetime, timedelta, timezone

from jose import jwt
from jose import JWTError  # noqa: F401 — re-exported so callers only import from here

from lib.config.settings import AppConfig

_DEV_SECRET = "dev-secret-change-in-production"
_SECRET_KEY = os.getenv("JWT_SECRET_KEY", _DEV_SECRET)
_ALGORITHM = "HS256"
_EXPIRE_MINUTES = 60


def _check_jwt_secret(key: str, strict: bool) -> None:
    """Warn or hard-fail if key is the insecure dev default."""
    if key != _DEV_SECRET:
        return
    msg = (
        "JWT_SECRET_KEY is using the insecure default dev secret. "
        "Set JWT_SECRET_KEY in .secrets/.env before deploying."
    )
    if strict:
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)
    else:
        warnings.warn(msg, stacklevel=2)


_config = AppConfig()
_check_jwt_secret(_SECRET_KEY, strict=_config.jwt_strict or _config.api_only)


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

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_jwt.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run full suite**

```
pytest --tb=short -q
```

Expected: all 518 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add lib/auth/jwt_handler.py tests/test_jwt.py
git commit -m "feat: extract _check_jwt_secret; add jwt_strict AppConfig field"
```

---

## Task 3: RateLimiter class

**Files:**
- Create: `lib/api/rate_limiter.py`
- Create: `tests/test_rate_limiter.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_rate_limiter.py`:

```python
"""Unit tests for RateLimiter — in-memory fallback only (no Redis required)."""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from lib.api.rate_limiter import RateLimiter


def _req(host: str = "127.0.0.1") -> MagicMock:
    req = MagicMock()
    req.client.host = host
    return req


def test_allows_requests_under_limit():
    """Requests up to the limit succeed without raising."""
    limiter = RateLimiter(limit=3, window=60)
    req = _req()
    for _ in range(3):
        limiter(req)  # no exception


def test_raises_429_when_limit_exceeded():
    """The request immediately after the limit raises HTTP 429."""
    limiter = RateLimiter(limit=3, window=60)
    req = _req()
    for _ in range(3):
        limiter(req)
    with pytest.raises(HTTPException) as exc:
        limiter(req)
    assert exc.value.status_code == 429
    assert exc.value.detail == "Too many requests"


def test_tracks_clients_independently():
    """Filling one client's bucket does not affect a different client."""
    limiter = RateLimiter(limit=2, window=60)
    for _ in range(2):
        limiter(_req("10.0.0.1"))
    limiter(_req("10.0.0.2"))  # different client — no exception


def test_expired_timestamps_are_evicted():
    """Timestamps older than window are discarded; bucket refills after window."""
    import time
    limiter = RateLimiter(limit=2, window=1)  # 1-second window
    req = _req()
    for _ in range(2):
        limiter(req)
    time.sleep(1.05)
    limiter(req)  # window expired — no exception
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_rate_limiter.py -v
```

Expected: FAIL — `lib.api.rate_limiter` module does not exist.

- [ ] **Step 3: Create `lib/api/rate_limiter.py`**

```python
"""
RateLimiter — sliding-window rate limiter as a FastAPI dependency.

Uses Redis via CacheRegistry when available; falls back to an in-process
dict (safe for single-process / test deployments).

Usage:
    limiter = RateLimiter(limit=60, window=60)

    @router.get("/")
    def endpoint(_: None = Depends(limiter)):
        ...
"""
from __future__ import annotations

import time

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, limit: int, window: int = 60):
        self._limit = limit
        self._window = window
        self._local: dict[str, list[float]] = {}

    def __call__(self, request: Request) -> None:
        key = f"rl:{request.client.host}"
        if self._redis_available():
            self._check_redis(key)
        else:
            self._check_local(key)

    def _redis_available(self) -> bool:
        try:
            from lib.services.cache_registry import CacheRegistry
            CacheRegistry.get("redis")
            return True
        except Exception:
            return False

    def _check_redis(self, key: str) -> None:
        from lib.services.cache_registry import CacheRegistry
        r = CacheRegistry.get("redis")._r
        now = time.time()
        pipe = r.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, 0, now - self._window)
        pipe.zcard(key)
        pipe.expire(key, self._window)
        _, _, count, _ = pipe.execute()
        if count > self._limit:
            raise HTTPException(status_code=429, detail="Too many requests")

    def _check_local(self, key: str) -> None:
        now = time.time()
        timestamps = self._local.get(key, [])
        cutoff = now - self._window
        timestamps = [t for t in timestamps if t > cutoff]
        timestamps.append(now)
        self._local[key] = timestamps
        if len(timestamps) > self._limit:
            raise HTTPException(status_code=429, detail="Too many requests")
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_rate_limiter.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Run full suite**

```
pytest --tb=short -q
```

Expected: all 518 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add lib/api/rate_limiter.py tests/test_rate_limiter.py
git commit -m "feat: add RateLimiter sliding-window dependency with Redis/in-memory fallback"
```

---

## Task 4: V1 contract router

**Files:**
- Create: `lib/api/v1.py`

No dedicated tests yet — this module is exercised by Tasks 7–9.

- [ ] **Step 1: Create `lib/api/v1.py`**

```python
"""
V1 contract router — the single guard for the entire /v1/ API surface.

Every route module mounts through one of two sub-routers returned by
make_v1_router():

  public    — rate-limited at login rate; no Bearer required (login endpoint)
  protected — rate-limited at general rate + Bearer JWT required (all other routes)

Usage (in router_registry.py):
    v1_router, public, protected = make_v1_router(config)
    public.include_router(auth_routes.router)      # _PUBLIC_ROUTER = True
    protected.include_router(users_routes.router)
    v1_router.include_router(public)
    v1_router.include_router(protected)
    app.include_router(v1_router)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from lib.api.rate_limiter import RateLimiter
from lib.auth.dependencies import get_current_user


def make_v1_router(config) -> tuple[APIRouter, APIRouter, APIRouter]:
    """
    Build the /v1 contract router.

    Returns (v1_router, public, protected). Mount route modules into public or
    protected, include both into v1_router, then include v1_router into the app.
    """
    general_limiter = RateLimiter(limit=config.rate_limit_per_minute)
    login_limiter = RateLimiter(limit=config.rate_limit_login_per_minute)

    v1_router = APIRouter(prefix="/v1")
    public = APIRouter(dependencies=[Depends(login_limiter)])
    protected = APIRouter(
        dependencies=[Depends(general_limiter), Depends(get_current_user)]
    )

    return v1_router, public, protected
```

- [ ] **Step 2: Verify the module imports cleanly**

```
python -c "from lib.api.v1 import make_v1_router; print('ok')"
```

Expected: prints `ok` with no errors.

- [ ] **Step 3: Commit**

```bash
git add lib/api/v1.py
git commit -m "feat: add make_v1_router — public/protected sub-routers for /v1/ contract"
```

---

## Task 5: Route prefix changes + test fixture updates

**Files:**
- Modify: `lib/api/routes/auth.py`, `users.py`, `roles.py`, `caches.py`, `scheduler.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_api.py`, `test_auth_api.py`, `test_api_routes.py`, `test_api_caches.py`, `test_api_roles_assign.py`, `test_auth_me.py`

All changes in this task must be applied together before running the test suite.

- [ ] **Step 1: Update route module prefixes**

In each file, change the `APIRouter(prefix=...)` call:

**`lib/api/routes/auth.py`** — line 18. Add `_PUBLIC_ROUTER` before the router:
```python
# Before:
router = APIRouter(prefix="/v1/auth", tags=["auth"])

# After:
_PUBLIC_ROUTER = True  # mount into public sub-router — login needs no Bearer
router = APIRouter(prefix="/auth", tags=["auth"])
```

**`lib/api/routes/users.py`** — line 29:
```python
# Before:
router = APIRouter(prefix="/v1/users", tags=["users"])

# After:
router = APIRouter(prefix="/users", tags=["users"])
```

**`lib/api/routes/roles.py`** — line 23:
```python
# Before:
router = APIRouter(prefix="/v1/roles", tags=["roles"])

# After:
router = APIRouter(prefix="/roles", tags=["roles"])
```

**`lib/api/routes/caches.py`** — line 26:
```python
# Before:
router = APIRouter(prefix="/v1/caches", tags=["caches"])

# After:
router = APIRouter(prefix="/caches", tags=["caches"])
```

**`lib/api/routes/scheduler.py`** — line 6:
```python
# Before:
router = APIRouter(prefix="/v1/scheduler", tags=["scheduler"])

# After:
router = APIRouter(prefix="/scheduler", tags=["scheduler"])
```

- [ ] **Step 2: Add `_v1_app` helper to `tests/conftest.py` and update `http_app`**

Add this function to `tests/conftest.py` just before the `# ── HTTP adapter test infrastructure ─────` comment:

```python
def _v1_app(*routers):
    """
    Build a test FastAPI app serving the given routers under /v1/ with no
    rate limiting or auth enforcement. Preserves /v1/... URL patterns after
    route modules dropped their /v1 prefix.
    """
    from fastapi import FastAPI, APIRouter
    v1 = APIRouter(prefix="/v1")
    for r in routers:
        v1.include_router(r)
    app = FastAPI()
    app.include_router(v1)
    return app
```

Replace the `http_app` fixture body:

```python
@pytest.fixture
def http_app(http_factory):
    """FastAPI app with all v1 routes — used by http_backend fixture."""
    from lib.api.routes import (
        auth as auth_routes,
        users as users_routes,
        roles as roles_routes,
        scheduler as scheduler_routes,
    )
    return _v1_app(
        auth_routes.router,
        users_routes.router,
        roles_routes.router,
        scheduler_routes.router,
    )
```

- [ ] **Step 3: Update `tests/test_api.py` — `api_client` fixture**

Add import at the top of the file (after existing imports):
```python
from tests.conftest import _v1_app
```

In the `api_client` fixture, replace:
```python
app = FastAPI()
app.include_router(users_routes.router)
```
with:
```python
app = _v1_app(users_routes.router)
```

Remove `from fastapi import FastAPI` if it's no longer used elsewhere in the file.

- [ ] **Step 4: Update `tests/test_auth_api.py` — `auth_client` fixture**

Add import:
```python
from tests.conftest import _v1_app
```

In the `auth_client` fixture, replace:
```python
app = FastAPI()
app.include_router(auth_router)
```
with:
```python
app = _v1_app(auth_router)
```

- [ ] **Step 5: Update `tests/test_api_routes.py` — `api_client` fixture**

Add import:
```python
from tests.conftest import _v1_app
```

In the `api_client` fixture, replace:
```python
app = FastAPI()
app.include_router(roles_routes.router)
app.include_router(users_routes.router)
```
with:
```python
app = _v1_app(roles_routes.router, users_routes.router)
```

- [ ] **Step 6: Update `tests/test_api_caches.py` — `client` fixture**

Add import:
```python
from tests.conftest import _v1_app
```

In the `client` fixture, replace:
```python
app = FastAPI()
app.include_router(caches_routes.router)
```
with:
```python
app = _v1_app(caches_routes.router)
```

- [ ] **Step 7: Update `tests/test_api_roles_assign.py` — `assign_client` fixture**

Add import:
```python
from tests.conftest import _v1_app
```

In the `assign_client` fixture, replace:
```python
app = FastAPI()
app.include_router(roles_routes.router)
app.include_router(users_routes.router)
```
with:
```python
app = _v1_app(roles_routes.router, users_routes.router)
```

- [ ] **Step 8: Update `tests/test_auth_me.py` — `auth_client` fixture**

Add import:
```python
from tests.conftest import _v1_app
```

In the `auth_client` fixture, replace:
```python
app = FastAPI()
app.include_router(auth_routes.router)
app.include_router(users_routes.router)
```
with:
```python
app = _v1_app(auth_routes.router, users_routes.router)
```

- [ ] **Step 9: Run the full test suite**

```
pytest --tb=short -q
```

Expected: all 518 tests PASS. If any test fails with a 404, the `_v1_app` wrapper is missing
from that fixture — apply Steps 3–8 to the failing file.

- [ ] **Step 10: Commit**

```bash
git add lib/api/routes/auth.py lib/api/routes/users.py lib/api/routes/roles.py lib/api/routes/caches.py lib/api/routes/scheduler.py
git add tests/conftest.py tests/test_api.py tests/test_auth_api.py tests/test_api_routes.py tests/test_api_caches.py tests/test_api_roles_assign.py tests/test_auth_me.py
git commit -m "refactor: move /v1 prefix to v1_router; update test fixtures with _v1_app"
```

---

## Task 6: Router registry + main.py CORS

**Files:**
- Modify: `lib/api/router_registry.py`
- Modify: `main.py`

- [ ] **Step 1: Replace `lib/api/router_registry.py`**

```python
"""
mount_routes — auto-discover and mount every router in lib/api/routes/.

Each route module is mounted through the v1 contract router:
  - Modules with _PUBLIC_ROUTER = True → public sub-router (rate limited, no auth)
  - All other modules → protected sub-router (rate limited + Bearer JWT)

Drop a new file in routes/ that defines `router = APIRouter(...)` and it is
protected automatically — no manual registration, no forgotten auth.
"""
from __future__ import annotations

import importlib
import pkgutil
from fastapi import FastAPI


def mount_routes(app: FastAPI, config, package: str = "lib.api.routes") -> None:
    from lib.api.v1 import make_v1_router
    v1_router, public, protected = make_v1_router(config)

    mod = importlib.import_module(package)
    for _, name, _ in pkgutil.iter_modules(mod.__path__):
        sub = importlib.import_module(f"{package}.{name}")
        if not hasattr(sub, "router"):
            continue
        if getattr(sub, "_PUBLIC_ROUTER", False):
            public.include_router(sub.router)
        else:
            protected.include_router(sub.router)

    v1_router.include_router(public)
    v1_router.include_router(protected)
    app.include_router(v1_router)
```

- [ ] **Step 2: Update `main.py` — add CORSMiddleware and pass config to mount_routes**

In `main.py`, locate the block that creates `api_app` and calls `mount_routes`. It currently looks like:

```python
api_app = FastAPI(title=config.app_title)
api_app.middleware("http")(log_requests)
mount_routes(api_app)
```

Replace it with:

```python
from fastapi.middleware.cors import CORSMiddleware

api_app = FastAPI(title=config.app_title)
api_app.middleware("http")(log_requests)
_cors_origins = [o.strip() for o in config.cors_origins.split(",") if o.strip()]
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
mount_routes(api_app, config)
```

- [ ] **Step 3: Run full test suite**

```
pytest --tb=short -q
```

Expected: all 518 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add lib/api/router_registry.py main.py
git commit -m "feat: wire v1 contract into router_registry; add CORSMiddleware to main.py"
```

---

## Task 7: Security contract tests

**Files:**
- Create: `tests/test_security_contract.py`

These tests audit the security contract structurally and behaviorally. A new route added
without auth will fail `test_protected_endpoints_require_bearer_token` immediately.

- [ ] **Step 1: Create `tests/test_security_contract.py`**

```python
"""
Security contract tests — structural + behavioral audit of the /v1/ API.

A new unprotected route will fail test_protected_endpoints_require_bearer_token.
Run after any change to lib/api/routes/ to verify the contract holds.
"""
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.config.settings import AppConfig
from lib.api.router_registry import mount_routes


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
def secured_app(monkeypatch):
    """Full v1 stack, in-memory DB, high rate limits so tests are never throttled."""
    import lib.models  # noqa: F401 — registers all ORM models in Base.metadata
    factory = _mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    config = AppConfig(rate_limit_per_minute=10000, rate_limit_login_per_minute=10000)
    app = FastAPI()
    mount_routes(app, config)
    return app


@pytest.fixture
def secured_client(secured_app):
    return TestClient(secured_app)


# ── Structural: all routes live under /v1/ ────────────────────────────────

def test_v1_prefix_on_all_routes(secured_app):
    """Every registered API route is under /v1/. Catches accidental top-level routes."""
    system_paths = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    api_routes = [
        r for r in secured_app.routes
        if isinstance(r, APIRoute) and r.path not in system_paths
    ]
    non_v1 = [r.path for r in api_routes if not r.path.startswith("/v1/")]
    assert non_v1 == [], f"Routes found outside /v1/: {non_v1}"


# ── Behavioral: login is the only public endpoint ─────────────────────────

def test_login_reaches_handler_without_token(secured_client):
    """Login is reachable without Bearer — returns handler error, not middleware 401."""
    resp = secured_client.post(
        "/v1/auth/login", data={"username": "nosuchuser", "password": "bad"}
    )
    assert resp.status_code == 401
    # "Invalid credentials" = handler ran. "Not authenticated" = auth middleware blocked.
    assert resp.json()["detail"] == "Invalid credentials"


def test_protected_endpoints_require_bearer_token(secured_client):
    """Every non-login endpoint returns 401 'Not authenticated' when no Bearer is sent."""
    endpoints = [
        ("GET", "/v1/users"),
        ("GET", "/v1/roles"),
        ("GET", "/v1/auth/me"),
        ("GET", "/v1/caches/"),
        ("GET", "/v1/scheduler/jobs"),
    ]
    for method, path in endpoints:
        resp = secured_client.request(method, path)
        assert resp.status_code == 401, (
            f"Expected 401 for {method} {path}, got {resp.status_code}"
        )
        assert resp.json()["detail"] == "Not authenticated", (
            f"{method} {path}: expected 'Not authenticated', got {resp.json()['detail']!r}"
        )
```

- [ ] **Step 2: Run to verify all 4 tests pass**

```
pytest tests/test_security_contract.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 3: Run full suite**

```
pytest --tb=short -q
```

Expected: all existing + 4 new tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_security_contract.py
git commit -m "test: add security contract audit — v1 prefix + opt-out auth enforcement"
```

---

## Task 8: Security behaviour tests

**Files:**
- Create: `tests/test_security_behaviour.py`

- [ ] **Step 1: Create `tests/test_security_behaviour.py`**

```python
"""
Runtime security behaviour — auth flow, 401 rejection, and 429 rate limiting.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.config.settings import AppConfig
from lib.api.router_registry import mount_routes
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
def secured_client(monkeypatch):
    """Full v1 stack with a test user. Low rate limits so 429 tests trigger fast."""
    import lib.models  # noqa: F401
    factory = _mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    config = AppConfig(rate_limit_per_minute=5, rate_limit_login_per_minute=3)
    app = FastAPI()
    mount_routes(app, config)
    UserService(factory).create_user(
        username="sectest", email="sec@test.com", password="pass123"
    )
    return TestClient(app)


def _login(client) -> str:
    """Log in as sectest; return the Bearer token string."""
    resp = client.post(
        "/v1/auth/login", data={"username": "sectest", "password": "pass123"}
    )
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth flow ──────────────────────────────────────────────────────────────

def test_login_returns_bearer_token(secured_client):
    token = _login(secured_client)
    assert isinstance(token, str) and len(token) > 10


def test_login_wrong_password_returns_401(secured_client):
    resp = secured_client.post(
        "/v1/auth/login", data={"username": "sectest", "password": "wrongpass"}
    )
    assert resp.status_code == 401


def test_protected_route_no_token_returns_401(secured_client):
    resp = secured_client.get("/v1/users")
    assert resp.status_code == 401


def test_protected_route_bad_token_returns_401(secured_client):
    resp = secured_client.get(
        "/v1/users", headers={"Authorization": "Bearer garbage.token.value"}
    )
    assert resp.status_code == 401


def test_protected_route_valid_token_returns_200(secured_client):
    token = _login(secured_client)
    resp = secured_client.get("/v1/users", headers=_bearer(token))
    assert resp.status_code == 200


# ── Rate limiting ─────────────────────────────────────────────────────────

def test_login_rate_limit_triggers_429(secured_client):
    """rate_limit_login_per_minute=3 → 4th request to /v1/auth/login is 429."""
    for _ in range(3):
        secured_client.post("/v1/auth/login", data={"username": "x", "password": "x"})
    resp = secured_client.post("/v1/auth/login", data={"username": "x", "password": "x"})
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Too many requests"


def test_general_rate_limit_triggers_429(secured_client):
    """rate_limit_per_minute=5 → 6th GET /v1/users in the same window is 429."""
    token = _login(secured_client)
    for _ in range(5):
        secured_client.get("/v1/users", headers=_bearer(token))
    resp = secured_client.get("/v1/users", headers=_bearer(token))
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Too many requests"
```

- [ ] **Step 2: Run to verify all 7 tests pass**

```
pytest tests/test_security_behaviour.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 3: Run full suite**

```
pytest --tb=short -q
```

Expected: all existing + 7 new tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_security_behaviour.py
git commit -m "test: add security behaviour tests — auth flow, 401, 429 rate limiting"
```

---

## Task 9: Security CORS tests

**Files:**
- Create: `tests/test_security_cors.py`

- [ ] **Step 1: Create `tests/test_security_cors.py`**

```python
"""CORS policy — Access-Control header tests for allowed and blocked origins."""
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lib.database.session import ConnectionRegistry, SessionFactory
from lib.database.base import Base
from lib.config.settings import AppConfig
from lib.api.router_registry import mount_routes

_ALLOWED = "http://localhost:3000"
_BLOCKED = "https://evil.com"


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
def cors_client(monkeypatch):
    """App with CORS configured to allow _ALLOWED only."""
    import lib.models  # noqa: F401
    factory = _mem_factory()
    factory.create_tables(Base)
    monkeypatch.setattr(ConnectionRegistry, "_factories", {"postgres": factory})
    config = AppConfig(
        cors_origins=_ALLOWED,
        rate_limit_per_minute=10000,
        rate_limit_login_per_minute=10000,
    )
    app = FastAPI()
    origins = [o.strip() for o in config.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    mount_routes(app, config)
    return TestClient(app, raise_server_exceptions=False)


def test_cors_allows_configured_origin(cors_client):
    """Preflight from an allowed origin returns the origin in the response header."""
    resp = cors_client.options(
        "/v1/auth/login",
        headers={"Origin": _ALLOWED, "Access-Control-Request-Method": "POST"},
    )
    assert resp.headers.get("access-control-allow-origin") == _ALLOWED


def test_cors_blocks_unknown_origin(cors_client):
    """Preflight from an unknown origin does not echo that origin back."""
    resp = cors_client.options(
        "/v1/auth/login",
        headers={"Origin": _BLOCKED, "Access-Control-Request-Method": "POST"},
    )
    origin_header = resp.headers.get("access-control-allow-origin", "")
    assert origin_header != _BLOCKED


def test_cors_credentials_allowed(cors_client):
    """Preflight response includes Access-Control-Allow-Credentials: true."""
    resp = cors_client.options(
        "/v1/auth/login",
        headers={"Origin": _ALLOWED, "Access-Control-Request-Method": "POST"},
    )
    assert resp.headers.get("access-control-allow-credentials") == "true"
```

- [ ] **Step 2: Run to verify all 3 tests pass**

```
pytest tests/test_security_cors.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 3: Run full suite**

```
pytest --tb=short -q
```

Expected: all existing + 3 new tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_security_cors.py
git commit -m "test: add CORS tests — allowed origin, blocked origin, credentials"
```

---

## Task 10: Smoke test update

**Files:**
- Modify: `tests/test_smoke.py`

- [ ] **Step 1: Add new modules to the import list**

In `tests/test_smoke.py`, find the `@pytest.mark.parametrize` list of module paths. Add these
two entries after `"lib.api.router_registry"`:

```python
"lib.api.rate_limiter",
"lib.api.v1",
```

- [ ] **Step 2: Run smoke tests**

```
pytest tests/test_smoke.py -v
```

Expected: all smoke tests PASS including the two new module imports.

- [ ] **Step 3: Run full suite**

```
pytest --tb=short -q
```

Expected: all tests PASS. The final count should be 518 + 4 (settings) + 3 (jwt) + 4 (rate_limiter) + 2 (smoke) + 4 (contract) + 7 (behaviour) + 3 (cors) = **545 tests**.

- [ ] **Step 4: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: add lib.api.rate_limiter and lib.api.v1 to smoke test imports"
```

---

## Self-Review

**Spec coverage:**
- JWT strict mode → Tasks 1 (AppConfig field), 2 (`_check_jwt_secret`) ✓
- CORS → Task 6 (main.py CORSMiddleware), Task 9 (CORS tests) ✓
- Rate limiting → Task 3 (RateLimiter), Task 4 (v1.py), Task 8 (behaviour tests) ✓
- Opt-out auth → Task 4 (v1.py), Task 5 (route prefix + `_PUBLIC_ROUTER`), Task 6 (router_registry), Task 7 (contract tests) ✓
- `.secrets/.env` constraint → Task 1 (`env_file` change), noted in all fixtures ✓
- Smoke test → Task 10 ✓

**Placeholder scan:** None found.

**Type consistency:**
- `make_v1_router(config)` is defined in Task 4 and called in Task 6 (router_registry) ✓
- `RateLimiter(limit=..., window=...)` defined in Task 3, used in Task 4 ✓
- `_PUBLIC_ROUTER = True` set in Task 5 (auth.py), read in Task 6 (router_registry) ✓
- `_v1_app(*routers)` defined in Task 5 (conftest), imported in 6 test files in Task 5 ✓
- `_check_jwt_secret(key, strict)` defined in Task 2, tested in Task 2 ✓
- `AppConfig(rate_limit_per_minute=5, rate_limit_login_per_minute=3)` — valid kwargs ✓

**Build order dependency check:**
- Task 5 (prefix change) requires Task 4 (`v1.py`) to exist — but Task 5 doesn't call `make_v1_router` directly; that's Task 6. Tasks 4 and 5 are independent; either order works. ✓
- Task 6 (router_registry) requires Tasks 3 (RateLimiter), 4 (v1.py), 5 (route modules with new prefixes) ✓
- Tasks 7–9 require Task 6 (full stack works) ✓
