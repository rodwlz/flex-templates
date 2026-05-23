---
title: "Security Guide"
category: guide
audience: [developer, agent]
related:
  - ../core/ARCHITECTURE.md
  - ../reference/VAULT_USAGE.md
agent_priority: high
---

# Security Guide

FlexTemplates 2.0 ships with four security layers active by default. This guide explains what
each one does, how to configure it, and how to extend it.

---

## How routes are protected

Every `/v1/` route passes through one of two sub-routers built by `make_v1_router(config)` in
`lib/api/v1.py`:

| Sub-router | Who uses it | Enforces |
|---|---|---|
| `public` | `lib/api/routes/auth.py` only | Login rate limit |
| `protected` | Every other route module | General rate limit + Bearer JWT |

**The default is protected.** A new file dropped in `lib/api/routes/` is automatically in the
`protected` sub-router — no `Depends(get_current_user)` required. The only way to opt out is
to add `_PUBLIC_ROUTER = True` at the top of the module.

### Making a route public

```python
# lib/api/routes/webhooks.py

_PUBLIC_ROUTER = True          # ← this one line moves the whole module to the public router
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/stripe")
def stripe_webhook(payload: dict):
    ...
```

Only do this for endpoints that genuinely need no authentication (webhooks with their own
signature verification, health checks, etc.).

---

## Environment variables

All security variables live in `.secrets/.env` — never in the project root `.env`.

| Variable | Default | Effect |
|---|---|---|
| `JWT_SECRET_KEY` | `dev-secret-change-me` | Signs and verifies all JWTs |
| `JWT_STRICT` | `false` | `true` → hard-fail on startup if dev secret is still set |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8080` | Comma-separated allowed origins |
| `RATE_LIMIT_PER_MINUTE` | `60` | Max requests/min per IP on protected routes |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `5` | Max login attempts/min per IP |

### Minimal `.secrets/.env` for beta deployment

```bash
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
JWT_STRICT=true
CORS_ORIGINS=https://app.example.com
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_LOGIN_PER_MINUTE=5
```

---

## JWT configuration

`lib/auth/jwt_handler.py` reads `JWT_SECRET_KEY` at module import time. If the key is still
the insecure dev default (`dev-secret-change-me`), the behaviour depends on `JWT_STRICT`:

| `JWT_STRICT` | `API_ONLY` | On startup |
|---|---|---|
| `false` | `false` | `warnings.warn` — app starts, token is forgeable |
| `true` | any | `sys.exit(1)` — app refuses to start |
| any | `true` | `sys.exit(1)` — app refuses to start |

**Always set `JWT_STRICT=true` before any deployment outside a developer machine.**

### Generating a production secret

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output as `JWT_SECRET_KEY` in `.secrets/.env`.

---

## CORS

`CORSMiddleware` is added in `main.py` using `config.cors_origins`. The middleware reads the
comma-separated string and converts it to a list at startup.

```bash
# .secrets/.env
CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

For local development the defaults (`http://localhost:3000,http://localhost:8080`) cover the
most common dev server ports. Add any port you run a frontend on.

**`allow_credentials=True` is set** — cookies and `Authorization` headers work cross-origin.
If you set `CORS_ORIGINS=*` (all origins) you cannot use credentials; browsers will reject
the preflight. Specify explicit origins instead.

---

## Rate limiting

`lib/api/rate_limiter.py` implements a sliding-window rate limiter keyed by client IP.

- **Redis backend** — used automatically when `CacheRegistry` has a `"redis"` adapter
  registered. Uses a sorted-set pipeline (atomic, safe for multi-process deployments).
- **In-memory fallback** — used when Redis is not available. Safe for single-process
  deployments and all test runs.

The two limiters created by `make_v1_router`:

```python
# lib/api/v1.py
general_limiter = RateLimiter(limit=config.rate_limit_per_minute)   # protected routes
login_limiter   = RateLimiter(limit=config.rate_limit_login_per_minute)  # login only
```

When the limit is exceeded the response is `HTTP 429 Too many requests`.

### Using RateLimiter on a custom endpoint

```python
from fastapi import Depends
from lib.api.rate_limiter import RateLimiter

_strict_limiter = RateLimiter(limit=10, window=60)  # 10 req/min

@router.post("/expensive-operation")
def expensive(_, __=Depends(_strict_limiter)):
    ...
```

The `window` parameter (default 60 seconds) sets the sliding window size. Timestamps older
than `window` seconds are evicted before each check.

---

## Auth flow reference

```
POST /v1/auth/login
  form: username=alice&password=secret
  → 200 {"access_token": "eyJ...", "token_type": "bearer"}

GET /v1/users
  header: Authorization: Bearer eyJ...
  → 200 [...]
```

The JWT payload contains `{"sub": "<user_uuid>"}`. `get_current_user` in
`lib/auth/dependencies.py` decodes it and returns the `User` ORM object. Use
`Depends(get_current_user)` on any handler that needs the current user beyond what the
sub-router already enforces:

```python
from lib.auth.dependencies import get_current_user

@router.delete("/{id}")
def delete_user(id: uuid.UUID, current_user=Depends(get_current_user)):
    # current_user is the authenticated User object
    ...
```

For role-based access use `require_roles`:

```python
from lib.auth.dependencies import require_roles

@router.post("/admin/action")
def admin_action(current_user=Depends(require_roles(["admin"]))):
    ...
```

---

## Security test coverage

Three test files ship with the framework and run on every `pytest` invocation:

| File | What it verifies |
|---|---|
| `tests/test_security_contract.py` | All routes are under `/v1/`; login is reachable without Bearer; every other endpoint returns 401 without Bearer |
| `tests/test_security_behaviour.py` | Full auth flow; 401 on no/bad token; 429 on rate-limit breach |
| `tests/test_security_cors.py` | Allowed origin gets CORS headers; blocked origin doesn't; credentials header present |

`test_security_contract.py` is a living regression guard — if a developer adds an
unprotected route, `test_protected_endpoints_require_bearer_token` fails immediately.
