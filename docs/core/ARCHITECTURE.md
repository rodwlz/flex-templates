---
title: "Architecture Overview"
category: core
audience: [developer, agent]
related:
  - CONVENTIONS.md
  - CONTRACTS_GUIDE.md
  - ../guides/QUICKSTART.md
agent_priority: high
---

# FlexTemplates 2.0 — Architecture

> **Land here first.** This is the "you are here" map. Five-minute read; jump
> from here to the deeper docs once you know what you're looking for.

FlexTemplates 2.0 is a forkable Python framework: a Flet desktop UI, a FastAPI
HTTP backend, and a SQLAlchemy data layer, all sharing one process. Every
layer talks to its neighbours through standardized Pydantic contracts, so any
piece can be swapped without touching the rest.

---

## The LEGO pitch

Think of it as LEGO blocks:

- **Plugs** are Pydantic models — `ActionRequest`, `ActionResult`, `Event`.
- **Blocks** are services with one job each — `NavigationService`,
  `VaultService`, `ConnectionTester`, `CacheTester`.
- **Builder** is `main.py` — the only file that knows about concrete types.

Swap any block, the rest of the system can't tell. That's the architecture
in one sentence.

---

## The layer stack

```
main.py            ← wires everything (the only file that names concrete types)
  │
  ├── views/       ← Flet pages; receive services via props dict
  ├── api/routes/  ← FastAPI endpoints; receive services via Depends
  │
  ├── ui/          ← Flet building blocks (router, BaseView, components)
  │
  ├── services/    ← Business logic (NavigationService, VaultService, ...)
  ├── adapters/    ← Non-SQL backends (RedisAdapter, FileAdapter)
  │
  ├── auth/        ← JWT handler + RBAC dependencies (get_current_user, require_roles)
  ├── middleware/  ← JSON logging middleware + setup_logging()
  ├── tasks/       ← APScheduler wrapper (TaskScheduler)
  │
  ├── repositories/← CRUD on ORM models (UserRepository : AbstractRepository[User])
  ├── models/      ← SQLAlchemy ORM tables
  ├── database/    ← SessionFactory, ConnectionRegistry, UnitOfWork
  ├── security/    ← Vault (encrypted secrets store) + bcrypt password helpers
  ├── config/      ← AppConfig (pydantic-settings, reads .env) + vault CLI
  │
  ├── core/        ← IService, SimpleService, StagingService, EventBus
  └── contracts/   ← ActionRequest, ActionResult, Event (pure Pydantic)
```

Boundaries between layers are enforced — see [CONVENTIONS.md §6](CONVENTIONS.md)
for the import rules.

---

## How a request flows

### Example: clicking a nav button

```
User clicks NavButton("Products", "/products")
  ↓
NavButton.on_click() fires
  ↓
nav_service.execute(ActionRequest(action="visit", data={"url": "/products"}))
  ↓
NavigationService updates its history stack and publishes
  Event(type="nav.route_changed", payload={...})
  ↓
EventBus dispatches to subscribers
  ↓
FletNavigationAdapter is subscribed; sees the event; calls page.go("/products")
  ↓
Flet fires page.on_route_change
  ↓
FletRouter.route_change(page):
  - Parses "/products" → path + query
  - Matches against registered routes
  - Lazy-loads lib.views.products
  - Calls view(page, props) → ProductsView(page, props).render()
  ↓
ProductsView builds its content, gets wrapped with appbar/sidebar by BaseView
  ↓
Router appends to page.views and calls page.update()
  ↓
Flet repaints
```

`NavigationService` doesn't import Flet. `FletNavigationAdapter` is the one
piece that does — and it's small. Swap it out for a web adapter and the rest
of the stack doesn't notice.

---

## The core pieces

### Contracts — `lib/contracts/base.py`

Three Pydantic models, used everywhere:

```python
class ActionRequest(BaseModel):
    action: str                      # "test", "visit", "set", "create"
    data: dict[str, Any] = {}        # action-specific payload

class ActionResult(BaseModel):
    success: bool
    data: dict[str, Any] = {}
    events: list[Event] = []
    error: str | None = None

class Event(BaseModel):
    type: str                        # "user.created", "nav.route_changed"
    payload: dict[str, Any] = {}
```

That's the entire vocabulary the system uses to talk between layers.
Deep dive: [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md) — same file, no change needed.

### Services — `lib/services/`

Every service implements `IService.execute(ActionRequest) -> ActionResult`.
Most subclass `SimpleService` and get free dispatch + exception trapping:

```python
class ConnectionTester(SimpleService):
    """Actions: test
    test(data: {name}) -> {alive, latency_ms, error}"""

    def test(self, data: dict) -> dict:
        factory = ConnectionRegistry.get(data["name"])
        # ... probe and return dict; SimpleService wraps it
```

Real services live in `lib/services/`. The action signatures are pinned in
[CONVENTIONS.md §7](CONVENTIONS.md) — same file, no change needed.

### Registries — `ConnectionRegistry`, `CacheRegistry`

Class-level singletons. `main.py` registers everything at startup, the rest of
the code looks up by name:

```python
ConnectionRegistry.get("postgres")     # returns a SessionFactory
CacheRegistry.get("redis")             # returns a RedisAdapter
```

Registries are exempt from the props-dict rule — they're global lookup tables,
not stateful business logic.

### EventBus — `lib/core/events.py`

A pub/sub channel for cross-layer notifications. Services publish events;
adapters subscribe. The publisher never knows who's listening.

```python
event_bus.subscribe("nav.route_changed", on_route_changed_handler)
event_bus.publish(Event(type="nav.route_changed", payload={"url": "/login"}))
```

`NavigationService` publishes; `FletNavigationAdapter` listens and calls
`page.go()`. They're decoupled — swap the adapter, NavigationService is
untouched.

### Repositories — `lib/repositories/`

Data access. Every repo extends `AbstractRepository[T]` and gets free CRUD:

```python
class UserRepository(AbstractRepository[User]):
    model = User

# Usage:
repo = UserRepository(ConnectionRegistry.get("postgres"))
user = repo.create({"username": "alice", ...})
repo.list(status="admin")
```

Read [tests/test_repository_base.py](../tests/test_repository_base.py) for
the full CRUD contract spelled out.

### Router & BaseView — `lib/ui/`

`FletRouter` turns URLs into views. Two routing modes:

- **Convention:** `/products` → `lib.views.products.view(page, props)`
- **Named (for params):** `router.register("/products/{id}", "lib.views.product_detail")`

`BaseView` is the page template — every view subclasses it and only writes
`build_content()`. The appbar, sidebar, and dev nav come for free. Admin views
that require login subclass `ProtectedView(BaseView)` instead — redirect to
`/login` is automatic if `backend.current_user()` returns None.

```python
class ProductsView(BaseView):
    title = "Products"
    show_sidebar = True

    def build_content(self):
        return ft.Column([ft.Text("Product list")])

def view(page, props):     # required entry point
    return ProductsView(page, props).render()
```

### BackendAdapter — `lib/adapters/backend_adapter.py`

The plug between Flet admin views and the backend. `IBackendAdapter` exposes four
typed domain properties:

| Property | Interface | What it does |
|---|---|---|
| `backend.auth` | `IAuthAdapter` | `login()`, `logout()`, `current_user()` |
| `backend.users` | `IUserAdapter` | `list()`, `create()`, `delete()` |
| `backend.roles` | `IRoleAdapter` | `list()`, `create()`, `delete()`, `assign()`, `remove()` |
| `backend.scheduler` | `ISchedulerAdapter` | `list()` — read-only job inspector |

Two concrete implementations:

- **`ServiceBackendAdapter`** — in-process, calls Python services directly. Current default in `main.py`.
- **`HttpBackendAdapter`** — over HTTP, calls FastAPI `/v1/` endpoints. Drop-in replacement.

One-line swap in `main.py` switches the whole app:

```python
# In-process (default):
backend = ServiceBackendAdapter(factory, user_service, scheduler)

# HTTP (local or remote):
backend = HttpBackendAdapter(base_url="http://localhost:8080")
```

Both satisfy `IBackendAdapter`. Views never touch a URL — they call
`backend.auth.login()`, `backend.users.list()`, etc., and the concrete type
is an implementation detail of `main.py` only.

`ProtectedView(BaseView)` checks `backend.auth.current_user()` before rendering
and redirects to `/login` if the session is empty.

### Vault — `lib/security/`

Encrypted secrets store with a two-key design (master + confirm). Vault starts
**locked** — no auto-unlock at startup. The user unlocks it manually via the
`/security` view. After unlock, `main.py` wires vault-sourced DB and cache
connections via the `vault.unlocked` event.
Deep dive: [VAULT_USAGE.md](../reference/VAULT_USAGE.md).

### API server — `lib/api/`

`BackendServer` runs Uvicorn in a daemon thread, sharing the same Python
process and the same `ConnectionRegistry` as the Flet UI. Routes auto-discover
from `lib/api/routes/`. The HTTP `/caches/{name}` endpoint and the Flet admin
view both call the same `CacheTester` — that's the contract paying off.

---

## Where to go for what

| You want to… | Read |
|---|---|
| Understand the contract pattern in depth | [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md) |
| Know the naming / structure / import rules | [CONVENTIONS.md](CONVENTIONS.md) |
| Add a new SQL DB / cache / view / service | [ADDING_STUFF.md](../guides/ADDING_STUFF.md) |
| Use the snap-in API (`self.nav`, `self.vault`, `self.events`) | [WRAPPERS.md](../guides/WRAPPERS.md) |
| Protect API routes with JWT / RBAC | [API_DEVELOPMENT.md — Auth & RBAC](../guides/API_DEVELOPMENT.md) |
| Paginate and filter repository results | [API_DEVELOPMENT.md — Pagination](../guides/API_DEVELOPMENT.md) |
| Manage secrets | [VAULT_USAGE.md](../reference/VAULT_USAGE.md) |
| Deploy with Docker / API-only mode | [ONBOARDING_DEPLOYMENT.md](../guides/ONBOARDING_DEPLOYMENT.md) |
| See a complete worked example | [PONG_EXAMPLE.md](../examples/PONG_EXAMPLE.md) |
| Get the project booting locally | [QUICKSTART.md](../guides/QUICKSTART.md) |
| Write tests | [TESTING.md](../reference/TESTING.md) |

---

## File tour

| File | Purpose |
|---|---|
| `lib/contracts/base.py` | `ActionRequest`, `ActionResult`, `Event` |
| `lib/core/interfaces.py` | `IService`, `SimpleService`, `StagingService`, `IRepository` |
| `lib/core/events.py` | `EventBus` (pub/sub) |
| `lib/config/settings.py` | `AppConfig` (env vars + `.env`) |
| `lib/database/session.py` | `SessionFactory`, `ConnectionRegistry` |
| `lib/database/uow.py` | `UnitOfWork` for stage/preview/commit flows |
| `lib/database/query.py` | `safe_query()` (parameterized raw SQL) |
| `lib/models/user.py` | Example ORM model (`User`) |
| `lib/repositories/base.py` | `AbstractRepository[T]` (generic CRUD) |
| `lib/repositories/user_repository.py` | `UserRepository` (concrete) |
| `lib/services/navigation_service.py` | History stack, no Flet imports |
| `lib/services/connection_tester.py` | Probes any registered SQL connection |
| `lib/services/cache_tester.py` | Probes any registered cache adapter |
| `lib/services/cache_registry.py` | Named store of cache adapter instances |
| `lib/services/schema_inspector.py` | Reads tables/columns via SQLAlchemy `inspect` |
| `lib/services/nav.py` | Snap-in wrapper around NavigationService |
| `lib/adapters/redis_adapter.py` | Redis connector |
| `lib/adapters/file_adapter.py` | CSV/JSON/Parquet/Excel reader |
| `lib/security/vault.py` | Snap-in wrapper around VaultService |
| `lib/security/vault_service.py` | Encrypted-secrets service (IService) |
| `lib/security/crypto.py` | Fernet encrypt/decrypt (only file importing `cryptography`) |
| `lib/api/server.py` | `BackendServer` (Uvicorn in a daemon thread) |
| `lib/api/router_registry.py` | Auto-discovers `lib/api/routes/` modules |
| `lib/api/mount_service.py` | Auto-generates POST routes from a `SimpleService` |
| `lib/api/routes/users.py` | Manual REST endpoints for `User` |
| `lib/api/routes/auth.py` | `POST /auth/login` — OAuth2 password flow, returns Bearer JWT |
| `lib/api/routes/caches.py` | Cache adapter HTTP routes |
| `lib/auth/jwt_handler.py` | `create_token()` / `decode_token()` — HS256 JWT (python-jose) |
| `lib/auth/dependencies.py` | `get_current_user` + `require_roles(*roles)` FastAPI deps |
| `lib/middleware/logging.py` | `JsonFormatter`, `setup_logging()`, `log_requests` middleware |
| `lib/tasks/scheduler.py` | `TaskScheduler` — APScheduler wrapper with start/stop lifecycle |
| `lib/security/password.py` | `hash_password()` / `verify_password()` — bcrypt helpers |
| `lib/config/cli.py` | `flex-encrypt` / `flex-decrypt` entry points for vault management |
| `lib/ui/router.py` | `FletRouter` (URL → view) |
| `lib/ui/adapter.py` | `FletNavigationAdapter` (binds NavigationService → page) |
| `lib/ui/error_adapter.py` | `FletErrorAdapter` (snackbar / fatal dialog) |
| `lib/ui/layouts/base_view.py` | `BaseView` page template |
| `lib/ui/components/` | Reusable bits (NavBar, SideBar, StatusCard, ...) |
| `lib/views/home.py` etc. | Pages — one file per route |
| `lib/views/admin/databases.py` | Admin DB inspector — see this for the props pattern |
| `lib/adapters/backend_adapter.py` | `IBackendAdapter` ABC + `ServiceBackendAdapter` |
| `lib/ui/layouts/protected_view.py` | `ProtectedView` — auth guard, redirects to `/login` |
| `lib/views/login.py` | Login form — calls `backend.login()`, navigates on success |
| `lib/views/manage/users.py` | Paginated user list + create + delete (auth required) |
| `lib/views/manage/roles.py` | Role list + create + delete (auth required) |
| `lib/views/admin/scheduler.py` | Read-only APScheduler job inspector (auth required) |
| `lib/database/migrations/` | Alembic migration scripts — run `alembic upgrade head` |
| `lib/views/admin/caches.py` | Admin cache inspector |
| `games/` | Pong demo — proves the LEGO architecture |
| `main.py` | Boot sequence — only file that names concrete types |

---

## Testing

All 398 tests run on in-memory SQLite and a `FakePage` stand-in for `ft.Page`,
so the suite has no external dependencies and finishes in ~10 seconds.

Tests double as runnable specifications. A few that are worth reading as docs:

- [tests/test_interfaces.py](../tests/test_interfaces.py) — what
  `SimpleService.execute()` does with every kind of input
- [tests/test_session.py](../tests/test_session.py) — `ConnectionRegistry`
  and `SessionFactory.session()` semantics
- [tests/test_repository_base.py](../tests/test_repository_base.py) —
  the `AbstractRepository[T]` CRUD contract on a minimal Pet model
- [tests/test_navigation_service.py](../tests/test_navigation_service.py) —
  back/forward stack behaviour

Strategy and patterns: [TESTING.md](../reference/TESTING.md).

---

## Async in Flet — the short version

You usually don't write async code. Flet 0.84+ runs an event loop in the
background, but most event handlers are written as plain sync functions.

When you need an async block (e.g. probing a network resource without
blocking the UI), `lib/views/admin/databases.py` shows the pattern:

```python
async def _run_probe():
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as ex:
        results = await loop.run_in_executor(None, lambda: list(ex.map(self._probe, names)))
    # ... update UI from result

self.page.run_task(_run_probe)
```

Plain sync handlers are fine for everything else.

---

## Getting started

1. Boot the app locally — [QUICKSTART.md](../guides/QUICKSTART.md).
2. Read this doc plus [CONVENTIONS.md](CONVENTIONS.md) (~30 min total).
3. Skim [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md) for one canonical end-to-end
   walkthrough (`ConnectionTester`).
4. When adding code, look at [ADDING_STUFF.md](../guides/ADDING_STUFF.md) for recipes.

You've got the foundation. Now make it yours.
