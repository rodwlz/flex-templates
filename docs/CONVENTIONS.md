# FlexTemplates 2.0 — Conventions

Single source of truth for naming, module structure, and action contracts.
Read this before adding new code. Everything in this repo follows these rules.

---

## 1. Vault Key Conventions

Secrets live in the vault only — never in `.env` or plain config files.
Keys follow a fixed pattern so startup can auto-register connections without code changes.

| Pattern | Registers as | Example |
|---|---|---|
| `POSTGRES_URL` | `ConnectionRegistry.get("postgres")` | `postgresql://user:pass@host/db` |
| `DATABASE_<NAME>` | `ConnectionRegistry.get("<name>")` | `DATABASE_ANALYTICS` → `"analytics"` |
| `SERVICE_URL` | `CacheRegistry.get("<service>")` | `REDIS_URL` → `"redis"` |
| `SERVICE_URL_<ID>` | `CacheRegistry.get("<service>_<id>")` | `REDIS_URL_MAIN` → `"redis_main"` |
| `SERVICE_PASSWORD` | used during adapter construction | `REDIS_PASSWORD` |
| `SERVICE_PASSWORD_<ID>` | paired with `SERVICE_URL_<ID>` | `REDIS_PASSWORD_MAIN` |

**Rules:**
- `<NAME>` and `<ID>` are uppercase in vault keys, lowercase in registry names.
- `POSTGRES_URL` is the **only** special-cased key — it always maps to `"postgres"`.
- All other SQL databases use `DATABASE_<NAME>`.
- Cache services are registered only for entries in `_CACHE_BUILDERS` in `main.py`.
  To add a new cache type (e.g. Memcached), add one line there.

---

## 2. Registry Names

Registry names are derived mechanically from vault keys. Never choose them manually.

**ConnectionRegistry:**
```
POSTGRES_URL            → "postgres"
DATABASE_ANALYTICS      → "analytics"
DATABASE_LEGACY_CRM     → "legacy_crm"
```

**CacheRegistry:**
```
REDIS_URL               → "redis"
REDIS_URL_MAIN          → "redis_main"
REDIS_URL_SESSION_STORE → "redis_session_store"
```

**Looking up in code:**
```python
ConnectionRegistry.get("analytics")   # raises RuntimeError if not registered
CacheRegistry.get("redis_main")       # raises RuntimeError if not registered
```

---

## 3. Class Naming

| Type | Suffix | Examples |
|---|---|---|
| Business logic | `Service` | `UserService`, `NavigationService`, `CacheTester` |
| Named instance stores | `Registry` | `CacheRegistry`, `ConnectionRegistry` |
| Data access | `Repository` | `UserRepository`, `AbstractRepository` |
| Non-SQL backends | `Adapter` | `RedisAdapter`, `FileAdapter` |
| Page modules | `View` | `HomeView`, `AdminDatabasesView`, `LoginView` |
| Reusable UI pieces | purpose-named | `NavButton`, `StatusCard`, `AdminTabs`, `SideBar` |
| ORM models | plain noun | `User`, `Product`, `Order` |
| Pydantic contracts | plain noun or descriptor | `ActionRequest`, `ActionResult`, `Event`, `PongState` |

**No exceptions.** If a class's role matches one of the above, it gets the suffix.

---

## 4. Method Naming

### IService / SimpleService
```python
def execute(self, request: ActionRequest) -> ActionResult   # always this signature
def <action_name>(self, data: dict) -> dict                 # SimpleService: one method per action
def _helper(self, ...)                                      # private helpers: underscore prefix
```

`SimpleService` routes `ActionRequest.action` to the matching method by name.
Methods return a plain `dict` (auto-wrapped into `ActionResult`) or an `ActionResult` directly.
Any raised exception becomes `ActionResult(success=False, error=str(exc))` automatically.

### StagingService (preview/confirm flows)
```python
def stage(self, data: dict) -> dict      # flushes and returns diff preview
def confirm(self, data: dict) -> dict    # commits the staged transaction
def cancel(self, data: dict) -> dict     # rolls back (always succeeds)
def _stage_impl(self, uow, data: dict) -> dict   # override this in subclasses
```

### IRepository
```python
def get(self, id) -> T | None
def list(self, **filters) -> list[T]
def create(self, data: dict) -> T
def update(self, id, data: dict) -> T | None
def delete(self, id) -> bool
```

### BaseView
```python
def build_content(self) -> ft.Control   # required — the page body
def build_appbar(self) -> ft.AppBar     # optional override
def build_sidebar(self) -> ft.Control   # optional override
def build_bottombar(self) -> ft.AppBar  # optional override
def render(self) -> ft.View             # called by router — do not override
```

### IFlexComponent
```python
def build(self) -> ft.Control   # returns the Flet control
```

---

## 5. Module Structure

One responsibility per file. File name is snake_case of the primary class.

```
lib/
├── contracts/
│   └── base.py                 ← ActionRequest, ActionResult, Event (pure Pydantic)
│
├── core/
│   ├── interfaces.py           ← IService, SimpleService, StagingService, IRepository, IFlexComponent
│   └── events.py               ← EventBus
│
├── config/
│   └── settings.py             ← AppConfig (pydantic-settings, reads .env)
│
├── database/
│   ├── base.py                 ← DeclarativeBase (import this to inherit ORM models)
│   ├── session.py              ← SessionFactory, ConnectionRegistry
│   ├── query.py                ← safe_query(session, sql, **params)
│   └── uow.py                  ← UnitOfWork, _BoundSession
│
├── models/
│   └── <entity>.py             ← one ORM model per file (user.py → User)
│
├── repositories/
│   ├── base.py                 ← AbstractRepository[T] — generic CRUD
│   └── <entity>_repository.py ← one repository per model (user_repository.py → UserRepository)
│
├── services/
│   ├── navigation_service.py   ← NavigationService
│   ├── schema_inspector.py     ← SchemaInspector
│   ├── connection_tester.py    ← ConnectionTester
│   ├── cache_registry.py       ← CacheRegistry
│   ├── cache_tester.py         ← CacheTester
│   └── <domain>_service.py    ← new services go here
│
├── adapters/
│   ├── redis_adapter.py        ← RedisAdapter (non-SQL cache/data backends)
│   ├── file_adapter.py         ← FileAdapter
│   └── <name>_adapter.py      ← new adapters go here
│
├── security/
│   ├── crypto.py               ← encrypt/decrypt (only file importing cryptography)
│   ├── vault_store.py          ← read/write .secrets/vault.json
│   └── vault_service.py        ← VaultService (IService)
│
├── api/
│   ├── server.py               ← BackendServer (Uvicorn daemon thread)
│   ├── router_registry.py      ← auto-discovers lib/api/routes/ modules
│   ├── mount_service.py        ← mount_service() — auto-generates POST routes from SimpleService
│   └── routes/
│       ├── users.py            ← manual REST routes for User (/users)
│       ├── caches.py           ← cache adapter routes (/caches)
│       └── <resource>.py      ← new route files go here, auto-discovered on startup
│
├── ui/
│   ├── adapter.py              ← FletNavigationAdapter
│   ├── error_adapter.py        ← FletErrorAdapter
│   ├── router.py               ← FletRouter (URL → view module)
│   ├── components/
│   │   └── <name>.py           ← one component per file
│   └── layouts/
│       └── base_view.py        ← BaseView base class
│
└── views/
    ├── <page>.py               ← one view per file, URL = /filename
    └── admin/
        └── <page>.py           ← admin views, URL = /admin/filename
```

**Placement rules:**
- New SQL-backed feature? → model in `models/`, repository in `repositories/`, service in `services/`
- New cache/external service? → adapter in `adapters/`, registered in `_CACHE_BUILDERS` in `main.py`
- New API endpoint? → route file in `api/routes/` (auto-discovered, no wiring needed)
- New Flet page? → view file in `views/` (auto-routed by filename, no registration needed)
- New reusable UI piece? → component in `ui/components/`

---

## 6. Import Rules

These rules prevent circular imports and keep layers clean.

| Layer | May import | Must not import |
|---|---|---|
| `contracts/` | `pydantic` only | anything from `lib/` |
| `core/` | `contracts/` | `ui/`, `api/`, `views/`, `services/` |
| `models/` | `database/base.py` | services, views, API |
| `repositories/` | `core/`, `models/`, `database/` | services, views, API, ui |
| `services/` | `core/`, `contracts/`, `repositories/`, `database/` | `ui/`, `views/`, `api/` |
| `adapters/` | `core/`, `contracts/` | `ui/`, `views/`, `api/` |
| `api/routes/` | `services/`, `repositories/`, `contracts/` | `ui/`, `views/` |
| `ui/` | `core/`, `contracts/`, `services/` | `api/routes/`, `views/` (except router) |
| `views/` | `ui/`, `contracts/` — **via `props` dict only** | direct service imports |
| `main.py` | everything — this is the wiring file | — |

**The props dict rule:** Views never import services directly. They receive them through the `props` dict injected by the router:

```python
# WRONG — views importing services directly
from lib.services.user_service import UserService

# CORRECT — services arrive via props
def build_content(self):
    user_service = self.props["user_service"]
```

**Registry exemption:** `ConnectionRegistry` and `CacheRegistry` are class-level singletons (no instances, classmethods only — they live closer to module state than to a service). Views may import them directly to enumerate or look up registered names. The props rule applies to instance services with state, side effects, or business logic.

```python
# OK — registries are global lookup tables, not stateful services
from lib.database.session import ConnectionRegistry
from lib.services.cache_registry import CacheRegistry

names = ConnectionRegistry.list()
adapter = CacheRegistry.get("redis")
```

---

## 7. Action Reference

All services, all actions, what data goes in, what comes back.

### NavigationService
| Action | data in | data out |
|---|---|---|
| `visit` | `{url}` | `{url, can_go_back, can_go_forward, prev, next, back_stack, forward_stack}` |
| `back` | `{steps?}` (default 1) | same as visit |
| `forward` | `{steps?}` (default 1) | same as visit |
| `clear` | `{}` | same as visit |
| `current` | `{}` | same as visit |

### VaultService
| Action | data in | data out |
|---|---|---|
| `unlock` | `{key?}` | `{unlocked, is_first_run}` |
| `get` | `{key}` | `{key, value}` |
| `set` | `{key, value}` | `{key, value}` |
| `delete` | `{key}` | `{deleted_key}` |
| `list_keys` | `{}` | `{keys: [str]}` |
| `save` | `{confirm_key?}` | `{saved, count}` |
| `lock` | `{}` | `{locked}` |
| `status` | `{}` | `{unlocked, vault_exists, env_exists, ready}` |
| `bootstrap` | `{}` | `{master_key, confirm_key}` |

### SchemaInspector
| Action | data in | data out |
|---|---|---|
| `get_tables` | `{}` | `{tables: [str]}` |
| `get_schema` | `{table_name}` | `{table, columns: [{name, type, nullable, primary_key, default}]}` |

### ConnectionTester
| Action | data in | data out |
|---|---|---|
| `test` | `{name}` | `{alive, latency_ms, error}` |

`name` looks up the factory in `ConnectionRegistry`. Stateless singleton — one instance for the whole app.

### CacheTester
| Action | data in | data out |
|---|---|---|
| `test` | `{name}` | `{alive, latency_ms, info, error}` |

`name` looks up the adapter in `CacheRegistry`. Stateless singleton — one instance for the whole app.

### RedisAdapter
| Action | data in | data out |
|---|---|---|
| `get` | `{key}` | `{key, value, found}` |
| `set` | `{key, value, ttl?}` | `{key, stored}` |
| `delete` | `{key}` | `{deleted}` |
| `exists` | `{key}` | `{exists}` |
| `keys` | `{pattern?}` (default `*`) | `{keys: [str]}` |
| `expire` | `{key, seconds}` | `{set}` |
| `ttl` | `{key}` | `{ttl}` |

### FileAdapter
| Action | data in | data out |
|---|---|---|
| `read` | `{path, columns?, limit?}` | `{rows: [dict], count}` |
| `list` | `{path?}` (default base_path) | `{files: [str], path}` |

### StagingService (base for preview/confirm flows)
| Action | data in | data out |
|---|---|---|
| `stage` | `{...service-specific}` | `{preview: {new, modified, deleted}, ...custom}` |
| `confirm` | `{}` | `{confirmed: true}` |
| `cancel` | `{}` | `{cancelled: true}` |

---

## 8. Docstring Policy

Default: **no docstring.** Code is readable by the identifiers alone.

Add a docstring only when:
- The class has non-obvious actions (document each action inline, like `RedisAdapter` does)
- A method has a hidden constraint or surprising invariant
- The WHY of a decision would confuse a future reader

**Format for services with actions (the standard):**
```python
class MyAdapter(SimpleService):
    """
    Actions: get, set, delete

    get(data: {key}) -> {key, value, found}
    set(data: {key, value, ttl?}) -> {key, stored}
    delete(data: {key}) -> {deleted}
    """
```

**Never:**
- Multi-paragraph docstrings
- Google-style Args/Returns sections
- Comments that repeat what the code already says
- `# used by X` or `# added for Y` references

---

## 9. When to Use SimpleService vs Custom execute()

Both patterns are first-class. Pick by what your service actually needs.

### Use `SimpleService` (default choice)

When each action is a self-contained method that returns a dict:

```python
class OrderService(SimpleService):
    def create(self, data: dict) -> dict:
        return {"order_id": db.insert(data)}

    def cancel(self, data: dict) -> dict:
        db.delete(data["order_id"])
        return {}
```

Routing is automatic. Plain `dict` returns get wrapped into `ActionResult(success=True, data=...)`. Any raised exception becomes `ActionResult(success=False, error=...)`. Most services should look like this.

### Use custom `execute()` with `match` when:

1. **Action names collide with read-only properties** the class already exposes
   (e.g. `NavigationService` exposes `nav.current` as a property *and* an action — the SimpleService dispatcher would resolve `current` to the property's value, not a callable).

2. **Actions need argument coercion or merging before dispatch**
   (e.g. `int(data.get("steps", 1))`, normalizing optional flags, defaulting from class state).

3. **Every action returns `ActionResult` directly** with custom `events=[...]` payloads.
   The dict-auto-wrap shortcut adds no value here.

```python
class NavigationService(IService):
    def execute(self, request: ActionRequest) -> ActionResult:
        match request.action:
            case "back":
                return self._back(int(request.data.get("steps", 1)))
            case "current":
                return ActionResult(success=True, data=self._nav_state())
```

`NavigationService` and `VaultService` use this pattern intentionally. Don't refactor them to `SimpleService` — they hit reasons 1, 2, and 3.
