# Changelog

All notable changes to flex-templates. Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: `MAJOR.MINOR.PATCH` — MAJOR for breaking changes, MINOR for additive, PATCH for fixes.

---

## [2.1.0] — 2026-06-05

### Breaking
- **`lib/` is now a namespace package** — `lib/__init__.py` removed. Consumer projects
  must also remove their `lib/__init__.py` to enable automatic namespace merging (PEP 420).
  Projects that keep `__init__.py` will see their `lib/` shadow the framework's `lib/`.
  See `docs/guides/DOCKER_INTEGRATION.md` for the canonical integration pattern.

### Added
- `BackendServer.wait()` — public method to block on the server thread; replaces
  direct `server._thread.join()` access in forked projects.
- `docs/guides/DOCKER_INTEGRATION.md` — canonical multi-stage Dockerfile, namespace
  merge explanation, local dev setup, git submodule pattern.
- `pyrightconfig.json.template` — drop-in Pylance/pyright config for consumer projects
  to resolve `lib.*` imports in VSCode without manual `extraPaths` discovery.
- `CLAUDE.md` forking gotchas — documents namespace package requirement,
  `BackendServer.wait()`, and `RedisAdapter` dict-based API.

### Changed
- `RedisAdapter` docstring now leads with an explicit warning that all ops take/return
  dicts, not bare string keys. `redis.get("key")` raises `KeyError`; use
  `redis.get({"key": "..."})`.
- `pyproject.toml` — `namespaces = true` added to `[tool.setuptools.packages.find]`.

### Fixed
- `AUTH_LOGIN_URL` env var now controls the Swagger UI `tokenUrl` — override the
  default `/v1/auth/login` without editing source.
- `ConnectionRegistry` default name changed from `"default"` to `"postgres"` to match
  vault key convention (`DATABASE_POSTGRES` → `"postgres"`).

---

## [2.0.0] — 2026-05-20

Initial 2.0 release. Complete rewrite from v1.

### Architecture
- Single-process model: Flet UI + FastAPI backend share one `ConnectionRegistry`.
- All inter-layer communication via `ActionRequest` / `ActionResult` / `Event` contracts.
- `SimpleService` auto-dispatches by method name; exceptions become `ActionResult(success=False)`.
- `StagingService` for preview/confirm transaction flows (wraps `UnitOfWork`).
- `BackendServer` runs Uvicorn in a daemon thread; `daemon=True` means clean exit
  when Flet (main thread) closes.

### Included
- `SessionFactory` + `ConnectionRegistry` (multi-DB, named registries).
- `UnitOfWork` + `_BoundSession` (long-lived session for staged transactions).
- `AbstractRepository[T]` generic CRUD base.
- `UserRepository`, `RoleRepository`, `ProductRepository` reference implementations.
- `RedisAdapter` (dict-based API, `from_url()` constructor).
- `FileAdapter` (CSV/JSON/Parquet/Excel, path-traversal blocked).
- `VaultService` (Fernet-encrypted secrets, two-key design).
- `NavigationService` (browser-history stack, no Flet dependency).
- `BackendServer` + `RouterRegistry` (auto-discovers routes by filename).
- `mount_service()` — auto-generates HTTP POST routes from a `SimpleService`.
- `RateLimiter` — sliding-window, Redis-backed with in-process fallback.
- `TaskScheduler` — APScheduler wrapper.
- `EventBus` — lightweight pub/sub.
- `FletRouter` + `BaseView` + `ProtectedView` UI primitives.
- `FletNavigationAdapter` + `FletErrorAdapter`.
- Alembic migrations wired and ready (`run_migrations()` helper).
- `AppConfig` via pydantic-settings (`.env` → env vars → defaults).
- JWT auth (`create_token`, `decode_token`, `get_current_user`, `get_ws_user`).
- WebSocket infrastructure (`ConnectionManager`, `ws_router`, room-based broadcast).
- 631 tests, all passing.
