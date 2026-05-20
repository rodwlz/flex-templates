# FlexTemplates — Agent Context

> Read this file first. Fastest way to understand this codebase. ~2 minute read.

## What This Is

FlexTemplates 2.0 is a Python framework combining Flet (desktop UI), FastAPI
(REST backend), and SQLAlchemy (ORM) in a single process with a shared
dependency injection container. Every layer communicates exclusively through
three Pydantic contracts: `ActionRequest`, `ActionResult`, and `Event` —
no layer reaches across to another layer's internal types.

## Architecture (30 seconds)

```
main.py            <- wires everything (the only file that names concrete types)
  |
  +-- views/       <- Flet pages; receive services via props dict
  +-- api/routes/  <- FastAPI endpoints; receive services via Depends
  |
  +-- ui/          <- Flet building blocks (router, BaseView, components)
  |
  +-- services/    <- Business logic (NavigationService, VaultService, ...)
  +-- adapters/    <- Non-SQL backends (RedisAdapter, FileAdapter)
  |
  +-- repositories/<- CRUD on ORM models (UserRepository : AbstractRepository[User])
  +-- models/      <- SQLAlchemy ORM tables
  +-- database/    <- SessionFactory, ConnectionRegistry, UnitOfWork
  +-- security/    <- Vault (encrypted secrets store)
  +-- config/      <- AppConfig (pydantic-settings, reads .env)
  |
  +-- core/        <- IService, SimpleService, StagingService, EventBus
  +-- contracts/   <- ActionRequest, ActionResult, Event (pure Pydantic)
```

One rule: `main.py` is the **only** file that names concrete
implementations. Everything else depends on interfaces.

## Key Files

| File | Purpose |
|---|---|
| `main.py` | Only place that wires concrete classes — change DI here |
| `lib/contracts/base.py` | `ActionRequest`, `ActionResult`, `Event` — the plugs |
| `lib/core/interfaces.py` | `IService`, `IRepository`, `SimpleService`, `StagingService` |
| `lib/database/session.py` | `SessionFactory` + `ConnectionRegistry` |
| `lib/services/user_service.py` | Reference implementation (immediate + staged ops) |
| `lib/repositories/user_repository.py` | Reference repository (CRUD + relationships) |
| `lib/api/routes/users.py` | Reference API routes (3 endpoint types) |
| `tests/conftest.py` | Test fixtures — in-memory SQLite, service factories |

## Documentation Map

| Folder | Read When |
|---|---|
| `docs/core/` | Before writing **any** code — ARCHITECTURE -> CONVENTIONS -> CONTRACTS_GUIDE |
| `docs/guides/` | Building a specific feature — API_DEVELOPMENT or VIEW_DEVELOPMENT |
| `docs/reference/` | Looking up a pattern — DECISION_TREES, VAULT_USAGE, TESTING |
| `docs/troubleshooting/` | Something broke or smells wrong — TROUBLESHOOTING -> ANTI_PATTERNS |
| `docs/examples/` | Need a complete worked example — PONG_EXAMPLE, API_PATTERN_TEMPLATE |

## Reading Paths by Task

- **Add an API endpoint** -> `docs/guides/API_DEVELOPMENT.md` -> `docs/reference/DECISION_TREES.md`
- **Add a Flet view** -> `docs/guides/VIEW_DEVELOPMENT.md` -> `docs/guides/WRAPPERS.md`
- **Add a new entity (model -> repo -> service -> route)** -> `docs/examples/API_PATTERN_TEMPLATE.md`
- **Something is broken** -> `docs/troubleshooting/TROUBLESHOOTING.md`
- **Understand the system** -> `docs/core/ARCHITECTURE.md` -> `docs/core/CONVENTIONS.md`
- **Understand contracts** -> `docs/core/CONTRACTS_GUIDE.md`

## Top 5 Conventions That Surprise People

- **Vault key names mechanically derive registry names — never choose them by hand.**
  All SQL databases use `DATABASE_<NAME>` (e.g. `DATABASE_POSTGRES` → `"postgres"`,
  `DATABASE_ANALYTICS` → `"analytics"`). Cache services follow `SERVICE_URL[_<ID>]`.
  Uppercase in the vault, lowercase in the registry. `PRIMARY_DATABASE` env var names
  which registered DB the backend adapter targets (default `"postgres"`). Pick the
  wrong key and the connection silently never registers at startup.

- **Views must not import services — services arrive via the `props` dict.**
  Doing `from lib.services.user_service import UserService` in a view is a
  layering violation. The router injects services through `self.props`. The
  *only* exemption is `ConnectionRegistry` and `CacheRegistry`, which are
  class-level lookup tables, not stateful services.

- **`main.py` is the single file allowed to name concrete classes.**
  Every other module depends on interfaces (`IService`, `IRepository`,
  `SimpleService`). To swap an implementation — including swapping a Flet
  adapter for a web adapter — you edit `main.py` and nothing else.

- **`SimpleService` auto-dispatches by method name; raised exceptions become `ActionResult(success=False, error=...)`.**
  You write plain methods like `def create(self, data: dict) -> dict`, return a
  dict, and the framework wraps it. Don't call `self.execute(ActionRequest(...))`
  from inside the same service — call the method directly. Use a custom
  `execute()` with `match` only when action names collide with class properties
  (NavigationService) or you need argument coercion before dispatch.

- **API routes and view files are auto-discovered by filename — no central registration.**
  Drop a file in `lib/api/routes/` and the URL appears on startup; drop one in
  `lib/views/` and `/filename` routes to it. The flip side: filenames *are* the
  contract, so renaming `users.py` changes the URL.

## Top 3 Anti-Patterns to Avoid

- **Hardcoded service imports in services (Anti-Pattern 1 / 13).**
  Writing `self._user_service = UserService(factory)` inside another service's
  `__init__` breaks DI, makes the service untestable, and hides the dependency
  from callers. Inject everything through the constructor and wire it in `main.py`.

- **Repository returning raw ORM objects (Anti-Pattern 6).**
  Returning a SQLAlchemy `User` from a repo method lets the session close before
  the caller touches `user.roles`, producing `DetachedInstanceError` far from the
  bug. Return dicts (or Pydantic models) materialized inside the `with
  factory.session()` block.

- **Views importing services directly (Anti-Pattern 9).**
  `from lib.services.user_service import UserService` inside a view file is the
  fastest way to make the view untestable and tightly bound to a concrete
  implementation. Always pull services from `self.props["<service_name>"]`.

## Three Endpoint Types

Every API operation is one of three types. Choose before writing a route:

| Type | When | Example |
|---|---|---|
| Immediate | Simple CRUD, low risk | `GET /users`, `DELETE /users/{id}` |
| Staged | Multi-step, has relationships | `POST /users/with-roles/stage -> confirm/cancel` |
| Approval-required | Bulk ops, irreversible | `POST /users/bulk-delete/request -> approve -> confirm` |

See `docs/reference/DECISION_TREES.md` for the full decision logic.
