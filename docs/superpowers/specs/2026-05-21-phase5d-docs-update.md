# Phase 5D — Documentation Update Spec

## Goal

Update the FlexTemplates docs to reflect Phase 5C additions (HttpBackendAdapter, /v1 API versioning, four new endpoints) and restructure for clarity. Remove the hand-written route catalog in favor of FastAPI's live auto-docs at `/docs`.

## Audience & Format

- **HTML** (`docs/api-docs/`) — what the developer reads in a browser
- **Markdown** (`docs/`) — what agents (Claude, etc.) read; leaner, no decorative prose

---

## HTML Changes

### `architecture.html` — Add Backend Adapter section

Add a new subsection after the existing service/repository layers titled **"Backend Adapter"**:

- Introduce `IBackendAdapter` as the interface with four domain properties: `auth`, `users`, `roles`, `scheduler`
- Explain the two concrete implementations:
  - `ServiceBackendAdapter` — in-process, calls services directly, current default in `main.py`
  - `HttpBackendAdapter` — over HTTP, calls FastAPI endpoints, drop-in replacement
- Show the one-line swap in `main.py`:

```python
# In-process (default):
backend = ServiceBackendAdapter(factory, user_service, scheduler)

# HTTP (local or remote):
backend = HttpBackendAdapter(base_url="http://localhost:8080")
```

- Explain `/v1/` prefix as the **universal contract** — the bridge between the Python adapter layer and any external client:
  - `HttpBackendAdapter` calls exactly these URLs (e.g. `POST /v1/auth/login`, `GET /v1/users/`). The adapter doesn't know whether it's talking to a local dev server or a remote production host — it just calls `/v1/...` and trusts the contract
  - `ServiceBackendAdapter` bypasses HTTP entirely and calls Python methods directly — but the result is identical because both implement `IBackendAdapter`
  - Any external client — JS dashboard, mobile app, CLI tool, card game backend — can call the same `/v1/` URLs and get the same contract the Python app uses. Write the endpoint once, consume from anywhere
  - The version prefix enables running `/v1/` and `/v2/` simultaneously during a migration: old clients keep working on `/v1/`, new clients adopt `/v2/`. No flag day, no breaking change
  - **The swap is transparent to views** because views call `backend.auth.login()`, never a URL. The URL is an implementation detail of `HttpBackendAdapter` only

### `api-development.html` — Replace route catalog with live link + guide

**Remove:**
- All hand-written route examples with hardcoded URLs (these are now stale and duplicated by FastAPI's `/docs`)
- The inline route catalog table

**Add at the top:**
A prominent banner:
> 📡 **Live API Reference** → `http://localhost:8080/docs` (Swagger UI) or `/redoc` (ReDoc) — run the app first

**Keep (updated):**
- How routes are auto-discovered from `lib/api/routes/` by filename
- The three endpoint types (immediate / staged / approval) — what each is for
- Auth dependency pattern (`Depends(get_current_user)`)
- Error handling pattern (`raise HTTPException`)

**Add — New Endpoints table:**

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/v1/auth/login` | POST | None | OAuth2 password flow, returns JWT |
| `/v1/auth/me` | GET | Bearer | Current user's full profile |
| `/v1/users/` | GET/POST/DELETE | Optional | User CRUD |
| `/v1/roles/` | GET/POST/DELETE | Optional | Role CRUD |
| `/v1/roles/assign` | POST | Optional | Assign role to user |
| `/v1/roles/remove` | DELETE | Optional | Remove role from user |
| `/v1/caches/` | GET/POST | Optional | Cache operations |
| `/v1/scheduler/jobs` | GET | Optional | List scheduled jobs |

Point to `/docs` for full request/response schemas.

### `http-mode.html` — New page

**Section 1: The Swap**

One-line change in `main.py` switches the entire app from in-process to HTTP:

```python
# Before (ServiceBackendAdapter — in-process):
backend = ServiceBackendAdapter(
    factory=factory,
    user_service=UserService(factory),
    scheduler=scheduler,
)

# After (HttpBackendAdapter — over HTTP):
from lib.adapters.http_backend_adapter import HttpBackendAdapter
backend = HttpBackendAdapter(base_url="http://localhost:8080")
```

Both satisfy `IBackendAdapter`. Views and services see no difference.

**Section 2: Security Rules**

- HTTPS required for any non-localhost URL — `ValueError` at construction time if violated
- Localhost variants allowed over HTTP: `localhost`, `127.0.0.1`, `::1`, `0.0.0.0`
- JWT token stored in RAM only (`_HttpSession._token`) — never logged, never written to disk
- Token cleared on `logout()` and on garbage collection of the adapter

**Section 3: Testing Pattern**

Use `_client=` escape hatch to inject a `TestClient` (bypasses URL validation, no real network):

```python
from fastapi.testclient import TestClient
from lib.adapters.http_backend_adapter import HttpBackendAdapter

backend = HttpBackendAdapter(base_url="http://testserver", _client=TestClient(app))
```

**Section 4: Why /v1/ Is the Contract**

Explain the versioning prefix as the glue between layers:

```
View code                    Always calls:  backend.auth.login()
                                                    ↓
ServiceBackendAdapter        Calls:         UserService.authenticate()  (Python, no HTTP)
HttpBackendAdapter           Calls:         POST /v1/auth/login          (HTTP)
                                                    ↓
FastAPI route                Handles:       POST /v1/auth/login
                             Calls:         UserService.authenticate()
```

Key points to make explicit in the page:
- The view never touches a URL. The URL lives inside `HttpBackendAdapter` only.
- `/v1/` is a stability promise to every external consumer (JS, mobile, CLI). Once published, it doesn't change without a version bump.
- Future proof: add `/v2/auth/login` without breaking existing clients. Both versions run side by side.
- The `ServiceBackendAdapter` skips the HTTP hop entirely but produces identical results — same service, same data, same `IBackendAdapter` interface.

**Section 5: When to Use Each Mode**

| Mode | Use when |
|---|---|
| `ServiceBackendAdapter` | Local Flet app, single process, direct DB access |
| `HttpBackendAdapter` | Remote backend, JS/mobile client, multi-process, microservice |

### `index.html` — Add HTTP Mode card

Add a new card to the **Builder Guides** section:

```
🔌 HTTP Mode
Switch from in-process to HTTP with one line. Covers HTTPS enforcement,
JWT handling, and the TestClient test pattern.
→ http-mode.html
```

Update the **API Development** card description:
> "Building routes, the three endpoint types, auth dependency, and error handling. Live API reference at `/docs`."

### `view-development.html` — Minor update

Update any examples that reference `backend.auth`, `backend.users`, etc. to reflect that `backend` is now `IBackendAdapter` (either Service or Http). No structural changes.

### `decision-trees.html` — Fix stale URLs

Update all route URL examples:
- `/roles` → `/v1/roles`
- `/users` → `/v1/users`
- `/auth/login` → `/v1/auth/login`
- `/caches` → `/v1/caches`

### `template.html` — Fix stale URLs

Same URL fixes as `decision-trees.html`. Update `ServiceBackendAdapter` references to `IBackendAdapter`.

### `troubleshooting.html` + `anti-patterns.html` — Minor additions

**Troubleshooting:** Add entry:
- *Symptom:* `ValueError: HTTPS required for non-localhost URL`
- *Cause:* `HttpBackendAdapter` constructed with an `http://` non-localhost URL
- *Fix:* Use `https://` for production URLs; `http://localhost` is allowed

**Anti-patterns:** Add entry:
- *Anti-pattern:* Hard-coding `ServiceBackendAdapter` type in views or services
- *Fix:* Always receive `IBackendAdapter` via `props["backend"]`; the concrete type is wired in `main.py` only

### `migrations.html` — No changes

---

## Markdown Changes

### `docs/guides/API_DEVELOPMENT.md` — Fix stale URLs

Update all route URL strings throughout the file:
- `/roles` → `/v1/roles`
- `/users` → `/v1/users`
- `/auth/login` → `/v1/auth/login`
- `/caches` → `/v1/caches`
- `tokenUrl="/auth/login"` → `tokenUrl="/v1/auth/login"`

Add a one-line note at the top of the route examples section:
> All routes are prefixed `/v1/` — FastAPI `/docs` is the canonical reference for full schemas.

### `docs/core/ARCHITECTURE.md` — Add HttpBackendAdapter

In the "Backend Adapters" section, add `HttpBackendAdapter` alongside `ServiceBackendAdapter`. Describe `IBackendAdapter` as the interface. Reference the one-line swap pattern.

### `docs/guides/EXTENDING_BACKEND.md` — Update adapter wiring section

Step 5 ("Add methods to ServiceBackendAdapter") currently only shows `ServiceBackendAdapter`. Add a note: if extending for HTTP use, add the same method to `HttpBackendAdapter` (or add it to `IBackendAdapter` if it should be universally available).

### `docs/core/CONVENTIONS.md` — Add /v1 versioning convention

Add the following to the conventions list:

> **All API routes use the `/v1/` prefix.** This is the universal contract that makes `HttpBackendAdapter` work — the adapter calls `/v1/...` URLs, and those same routes are what FastAPI exposes. Any external client (JS, mobile, CLI) targets the same prefix. Never skip the prefix in route definitions or test URLs. When breaking changes are needed, add a `/v2/` router alongside `/v1/` rather than modifying existing routes.

### `docs/reference/API_ARCHITECTURE_SUMMARY.md` — Delete

This file lists routes that are now maintained by FastAPI's `/docs`. Deleting removes a maintenance burden with no loss of information.

---

## Files Summary

| File | Action |
|---|---|
| `docs/api-docs/architecture.html` | Modify — add Backend Adapter section |
| `docs/api-docs/api-development.html` | Modify — replace route catalog with live link + new endpoints table |
| `docs/api-docs/http-mode.html` | Create — new HttpBackendAdapter page |
| `docs/api-docs/index.html` | Modify — add HTTP Mode card, update API card description |
| `docs/api-docs/view-development.html` | Modify — minor IBackendAdapter terminology update |
| `docs/api-docs/decision-trees.html` | Modify — fix stale URLs |
| `docs/api-docs/template.html` | Modify — fix stale URLs |
| `docs/api-docs/troubleshooting.html` | Modify — add HTTPS error entry |
| `docs/api-docs/anti-patterns.html` | Modify — add concrete-type-in-view anti-pattern |
| `docs/api-docs/migrations.html` | No change |
| `docs/api-docs/pong.html` | No change |
| `docs/guides/API_DEVELOPMENT.md` | Modify — fix all stale URLs |
| `docs/core/ARCHITECTURE.md` | Modify — add HttpBackendAdapter + IBackendAdapter |
| `docs/guides/EXTENDING_BACKEND.md` | Modify — update adapter wiring step |
| `docs/core/CONVENTIONS.md` | Modify — add /v1 convention |
| `docs/reference/API_ARCHITECTURE_SUMMARY.md` | Delete |
