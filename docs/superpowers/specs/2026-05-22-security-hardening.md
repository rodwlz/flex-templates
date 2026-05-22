# Security Hardening — FastAPI Backend

**Date:** 2026-05-22
**Status:** Approved

## Context

FlexTemplates 2.0 has a working FastAPI backend with JWT auth, but four security gaps exist before
exposing it to beta testers:

1. JWT dev-secret only hard-fails in `API_ONLY` mode — `JWT_SECRET_KEY` is silently forgeable
   in normal (Flet + API) mode.
2. No CORS policy — any origin can call the API.
3. No rate limiting on `/v1/auth/login` — brute-force / credential-stuffing attack surface.
4. Auth is opt-in per route — new routes start unauthenticated unless the developer remembers
   to add `Depends(get_current_user)`.

This spec fixes all four and adds test-enforced guards so they cannot regress.

---

## Environment Variable Constraint

**All new env vars (`JWT_SECRET_KEY`, `JWT_STRICT`, `CORS_ORIGINS`, `RATE_LIMIT_PER_MINUTE`,
`RATE_LIMIT_LOGIN_PER_MINUTE`) live in `.secrets/.env`.** Never in the project root.

`AppConfig.model_config` currently reads `env_file=".env"` (root). This must be updated to
`env_file=".secrets/.env"` so pydantic-settings picks up security vars from the right location.

---

## Fix 1 — JWT Strict Mode

### Problem

`lib/auth/jwt_handler.py` only `sys.exit(1)` when `API_ONLY=true`. In normal mode it emits a
`warnings.warn` — easy to miss, silently forgeable tokens in staging/prod.

### Design

Add `jwt_strict: bool = False` to `AppConfig`. When `True`, the module hard-fails regardless
of `API_ONLY`.

Set `JWT_STRICT=true` in `.secrets/.env` before any deployment outside a developer machine.

```python
# lib/auth/jwt_handler.py — new logic
_strict = config.jwt_strict or config.api_only

if _SECRET_KEY == _DEV_SECRET:
    _msg = (
        "JWT_SECRET_KEY is using the insecure default dev secret. "
        "Set JWT_SECRET_KEY in .secrets/.env before deploying."
    )
    if _strict:
        print(f"ERROR: {_msg}", file=sys.stderr)
        sys.exit(1)
    else:
        warnings.warn(_msg, stacklevel=2)
```

`jwt_handler.py` must import `AppConfig` at module load and cache the result — no circular
imports because `AppConfig` depends only on `pydantic-settings`.

---

## Fix 2 — CORS Policy

### Problem

No `CORSMiddleware` on the FastAPI app — any origin can make cross-origin requests.

### Design

Add `CORSMiddleware` in `main.py` using `cors_origins` from `AppConfig`.

```python
# AppConfig additions
cors_origins: str = "http://localhost:3000,http://localhost:8080"
```

`cors_origins` is a comma-separated string — `CORSMiddleware` wants a list.
Parse in `main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

origins = [o.strip() for o in config.cors_origins.split(",") if o.strip()]
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**`CORS_ORIGINS` in `.secrets/.env`** — comma-separated list of allowed origins.
Example for beta deployment:
```
CORS_ORIGINS=https://app.example.com,http://localhost:3000
```

---

## Fix 3 — Rate Limiting

### Problem

`POST /v1/auth/login` has no rate limit. An attacker can try unlimited passwords.

### Design

**`lib/api/rate_limiter.py`** — callable class usable as a FastAPI dependency.

```python
class RateLimiter:
    """
    Sliding-window rate limiter. Uses Redis via CacheRegistry if available;
    falls back to an in-process dict (safe for single-process deployments).

    Usage as a FastAPI dependency:
        limiter = RateLimiter(limit=60, window=60)

        @router.get("/")
        def endpoint(client=Depends(limiter)):
            ...

    Raises HTTP 429 when the limit is exceeded.
    """
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
        r = CacheRegistry.get("redis")._r  # raw redis client
        import time
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
        import time
        now = time.time()
        timestamps = self._local.get(key, [])
        cutoff = now - self._window
        timestamps = [t for t in timestamps if t > cutoff]
        timestamps.append(now)
        self._local[key] = timestamps
        if len(timestamps) > self._limit:
            raise HTTPException(status_code=429, detail="Too many requests")
```

**AppConfig additions:**

```python
rate_limit_per_minute: int = 60       # general /v1/ routes
rate_limit_login_per_minute: int = 5  # POST /v1/auth/login
```

---

## Fix 4 — Opt-Out Auth (V1 Contract Object)

### Problem

Auth is opt-in — routes are unauthenticated by default. Developers must remember to add
`Depends(get_current_user)` to every protected route.

### Design

**`lib/api/v1.py`** — the V1 contract object. Every `/v1/` route mounts through it.

```python
from fastapi import APIRouter, Depends
from lib.api.rate_limiter import RateLimiter
from lib.auth.dependencies import get_current_user

def make_v1_router(config) -> tuple[APIRouter, APIRouter, APIRouter]:
    """
    Returns (v1_router, public, protected).

    public    — /v1/ routes that require rate limiting only (login endpoint)
    protected — /v1/ routes that require rate limiting + valid Bearer JWT
    """
    general_limiter = RateLimiter(limit=config.rate_limit_per_minute)
    login_limiter   = RateLimiter(limit=config.rate_limit_login_per_minute)

    v1_router = APIRouter(prefix="/v1")

    public = APIRouter(dependencies=[Depends(login_limiter)])
    protected = APIRouter(dependencies=[Depends(general_limiter), Depends(get_current_user)])

    return v1_router, public, protected
```

**`lib/api/router_registry.py`** — updated to mount into the correct sub-router:

```python
def mount_routes(app: FastAPI, config, package: str = "lib.api.routes") -> None:
    from lib.api.v1 import make_v1_router
    v1_router, public, protected = make_v1_router(config)

    mod = importlib.import_module(package)
    for _, name, _ in pkgutil.iter_modules(mod.__path__):
        sub = importlib.import_module(f"{package}.{name}")
        if not hasattr(sub, "router"):
            continue
        # auth.py router declares itself public (login endpoint)
        if getattr(sub, "_PUBLIC_ROUTER", False):
            public.include_router(sub.router)
        else:
            protected.include_router(sub.router)

    v1_router.include_router(public)
    v1_router.include_router(protected)
    app.include_router(v1_router)
```

Route modules that should be public declare `_PUBLIC_ROUTER = True` at module level.
Only `lib/api/routes/auth.py` has this flag (login endpoint).

**Route module changes:**

Every route module's `APIRouter` prefix changes from `"/v1/..."` to `"/..."` — the `/v1/`
prefix is now owned by `v1_router`. Examples:

```python
# Before:
router = APIRouter(prefix="/v1/users", tags=["users"])

# After:
router = APIRouter(prefix="/users", tags=["users"])
```

Affected files: `auth.py`, `users.py`, `roles.py`, `caches.py`, `scheduler.py`.

`auth.py` also gets `_PUBLIC_ROUTER = True` at module level.

---

## File Map

| File | Action | Change |
|---|---|---|
| `lib/config/settings.py` | Modify | Add `cors_origins`, `rate_limit_per_minute`, `rate_limit_login_per_minute`, `jwt_strict`; change `env_file` to `.secrets/.env` |
| `lib/auth/jwt_handler.py` | Modify | Import `AppConfig`; use `config.jwt_strict` instead of bare `API_ONLY` check |
| `lib/api/rate_limiter.py` | Create | `RateLimiter` callable class |
| `lib/api/v1.py` | Create | `make_v1_router(config)` — returns `(v1_router, public, protected)` |
| `lib/api/router_registry.py` | Modify | Accept `config`; mount into `public`/`protected` instead of direct `app.include_router` |
| `lib/api/routes/auth.py` | Modify | Remove `/v1` from prefix; add `_PUBLIC_ROUTER = True` |
| `lib/api/routes/users.py` | Modify | Remove `/v1` from prefix |
| `lib/api/routes/roles.py` | Modify | Remove `/v1` from prefix |
| `lib/api/routes/caches.py` | Modify | Remove `/v1` from prefix (if `/v1` present) |
| `lib/api/routes/scheduler.py` | Modify | Remove `/v1` from prefix (if `/v1` present) |
| `main.py` | Modify | Add `CORSMiddleware`; pass `config` to `mount_routes` |
| `tests/test_security_contract.py` | Create | Audit tests — inspect route registry |
| `tests/test_security_behaviour.py` | Create | Behaviour tests — 401, 403, 429 responses |
| `tests/test_security_cors.py` | Create | CORS header tests |

---

## Security Tests

Three test files — each tests a distinct guarantee.

### `tests/test_security_contract.py` — Audit (structural)

These tests inspect the FastAPI route registry at import time. They enforce the security contract
even before any HTTP request is made. If a new route is added without auth, these tests catch it.

```
test_all_v1_routes_have_rate_limit
    → every route under /v1/ has RateLimiter in its dependency chain

test_protected_routes_require_auth
    → every route NOT in the public set has get_current_user in its dependency chain

test_only_login_is_public
    → only POST /v1/auth/login is in the public set (no other route lacks auth)

test_v1_prefix_present_on_all_routes
    → no route exists outside /v1/ (catches accidental top-level routes)
```

### `tests/test_security_behaviour.py` — Behaviour (runtime)

```
test_login_returns_token
    → POST /v1/auth/login with valid credentials returns {"access_token": ..., "token_type": "bearer"}

test_login_wrong_password_returns_401
    → POST /v1/auth/login with bad password → 401

test_protected_route_no_token_returns_401
    → GET /v1/users without Authorization header → 401

test_protected_route_bad_token_returns_401
    → GET /v1/users with Authorization: Bearer garbage → 401

test_protected_route_valid_token_returns_200
    → GET /v1/users with valid token → 200

test_login_rate_limit_triggers_429
    → POST /v1/auth/login N+1 times rapidly → 429 on the last one
    (use config with rate_limit_login_per_minute=3 for the test app)

test_general_rate_limit_triggers_429
    → GET /v1/users N+1 times rapidly → 429 on the last one
    (use config with rate_limit_per_minute=5 for the test app)
```

### `tests/test_security_cors.py` — CORS

```
test_cors_allows_configured_origin
    → OPTIONS request with Origin: http://localhost:3000 (in cors_origins) → 200
      response has Access-Control-Allow-Origin: http://localhost:3000

test_cors_blocks_unknown_origin
    → OPTIONS request with Origin: https://evil.com (not in cors_origins)
      response has no Access-Control-Allow-Origin header (or value is not https://evil.com)

test_cors_credentials_allowed
    → response has Access-Control-Allow-Credentials: true
```

---

## Constraints

- All new env vars live in `.secrets/.env` — never in the project root.
- `AppConfig.model_config` must use `env_file=".secrets/.env"` so pydantic-settings reads from
  the right location. This is a one-line change but unblocks all new security configuration.
- Rate limits in tests must be set low (3–5/min) so tests run fast without sleep loops.
  Pass a custom `AppConfig` instance to `make_v1_router` in test fixtures.
- `RateLimiter._check_local` uses wall-clock time — tests that hit rate limits must fire requests
  in a tight loop (no sleep) or mock `time.time`.
- The `_PUBLIC_ROUTER` sentinel is checked by `router_registry.py` at mount time. It is a
  module-level bool, not a route decorator — adding it to auth.py is a one-liner.
- No changes to `lib/auth/dependencies.py` — `get_current_user` and `require_roles` remain
  unchanged; they are still available for routes that need role-based access beyond the default
  auth check.

---

## Success Criteria

1. All 518 existing tests still pass after every step.
2. `test_security_contract.py` — 4 tests pass and will catch any future unprotected route.
3. `test_security_behaviour.py` — 7 tests pass.
4. `test_security_cors.py` — 3 tests pass.
5. Starting the app with `JWT_SECRET_KEY` unset and `JWT_STRICT=true` in `.secrets/.env`
   hard-fails with a clear error message.
6. `GET /v1/users` without a token returns 401.
