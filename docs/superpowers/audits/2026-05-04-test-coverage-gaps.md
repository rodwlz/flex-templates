# Test Coverage Gaps — Phase 2 Task 3

**Date:** 2026-05-04  
**Total test files:** 24  
**Total test lines:** 2,696  
**Test count:** 244 passing

## Summary

- **Total modules in `lib/`:** 51 (excluding `__init__.py`)
- **Modules with dedicated test files:** 21
- **Modules covered by smoke tests only:** 38 (imported once, no behavior tested)
- **Modules with zero coverage:** 1
- **Coverage by test type:**
  - Dedicated behavior tests (21 modules)
  - Integration tests (6 modules: `test_multidb_phase1_integration.py`, `test_api.py`)
  - Smoke tests only (38 modules: `test_smoke.py`)
  - Zero coverage (1 module)

## Test File Mapping

| Module | Test Coverage Type | Test File(s) |
|--------|------------------|--------------|
| `lib/contracts/base.py` | Dedicated | `test_contracts.py` (6 tests) |
| `lib/core/events.py` | Dedicated | `test_event_bus.py` (6 tests) |
| `lib/core/interfaces.py` | Smoke only | `test_smoke.py` |
| `lib/database/base.py` | Smoke only | `test_smoke.py` |
| `lib/database/session.py` | Integration | `test_api.py`, `test_multidb_phase1_integration.py` |
| `lib/database/query.py` | Smoke only | `test_smoke.py` |
| `lib/database/uow.py` | Dedicated | `test_uow.py` (13 tests) |
| `lib/database/migrations/env.py` | Zero coverage | None |
| `lib/models/user.py` | Smoke only | `test_smoke.py` |
| `lib/repositories/base.py` | Smoke only | `test_smoke.py` |
| `lib/repositories/user_repository.py` | Dedicated | `test_repositories.py` (10 tests) |
| `lib/adapters/file_adapter.py` | Dedicated | `test_adapters.py` (7 tests) |
| `lib/adapters/redis_adapter.py` | Dedicated | `test_adapters.py` (5 tests) |
| `lib/services/navigation_service.py` | Dedicated | `test_navigation_service.py` (18 tests) |
| `lib/services/nav.py` | Smoke only | `test_smoke.py` |
| `lib/services/schema_inspector.py` | Dedicated | `test_schema_inspector.py` (4 tests) |
| `lib/services/connection_tester.py` | Dedicated | `test_connection_tester.py` (class-based) |
| `lib/services/cache_registry.py` | Dedicated | `test_cache_registry.py` (5 tests) |
| `lib/services/cache_tester.py` | Dedicated | `test_cache_tester.py` (class-based) |
| `lib/security/crypto.py` | Smoke only | `test_smoke.py` |
| `lib/security/vault_store.py` | Smoke only | `test_smoke.py` |
| `lib/security/vault_service.py` | Dedicated | `test_vault_service.py` (13 tests) |
| `lib/security/vault.py` | Implicitly tested | `test_vault_service.py` |
| `lib/api/server.py` | Smoke only | `test_smoke.py` |
| `lib/api/mount_service.py` | Dedicated | `test_mount_service.py` (7 tests) |
| `lib/api/router_registry.py` | Smoke only | `test_smoke.py` |
| `lib/api/routes/users.py` | Integration | `test_api.py` (5 tests) |
| `lib/api/routes/caches.py` | Dedicated | `test_api_caches.py` (9 tests) |
| `lib/config/settings.py` | Dedicated | `test_settings.py` (7 tests) |
| `lib/ui/adapter.py` | Smoke only | `test_smoke.py` |
| `lib/ui/error_adapter.py` | Smoke only | `test_smoke.py` |
| `lib/ui/router.py` | Dedicated | `test_router.py` (10 tests) |
| `lib/ui/layouts/base_view.py` | Dedicated | `test_base_view.py` (12 tests) |
| `lib/ui/components/dev_nav.py` | Smoke only | `test_smoke.py` |
| `lib/ui/components/nav_button.py` | Smoke only | `test_smoke.py` |
| `lib/ui/components/back_button.py` | Smoke only | `test_smoke.py` |
| `lib/ui/components/nav_bar.py` | Smoke only | `test_smoke.py` |
| `lib/ui/components/side_bar.py` | Smoke only | `test_smoke.py` |
| `lib/ui/components/card.py` | Smoke only | `test_smoke.py` |
| `lib/ui/components/copy_button.py` | Smoke only | `test_smoke.py` |
| `lib/ui/components/admin_tabs.py` | Dedicated | `test_admin_tabs.py` (5 tests) |
| `lib/ui/components/status_card.py` | Dedicated | `test_status_card.py` (4 tests) |
| `lib/views/home.py` | Smoke only | `test_smoke.py` |
| `lib/views/login.py` | Smoke only | `test_smoke.py` |
| `lib/views/products.py` | Smoke only | `test_smoke.py` |
| `lib/views/product_detail.py` | Smoke only | `test_smoke.py` |
| `lib/views/security.py` | Smoke only | `test_smoke.py` |
| `lib/views/vault_test.py` | Smoke only | `test_smoke.py` |
| `lib/views/not_found.py` | Smoke only | `test_smoke.py` |
| `lib/views/admin/databases.py` | Dedicated | `test_admin_databases_view.py` (8 tests) |
| `lib/views/admin/caches.py` | Dedicated | `test_admin_caches_view.py` (8 tests) |

---

## Tier 1 (Critical) — 3 gaps

These are foundation layers. If they're broken, the entire app breaks. Some are exercised heavily via integration tests; others lack behavioral coverage.

### No Dedicated Coverage

- **`lib/database/migrations/env.py`** — Alembic environment configuration — **zero tests** — runs during schema migrations; if broken, new deployments fail silently. Critical infrastructure but rarely changes; integration test migration support exists but this file itself has no unit coverage.

- **`lib/database/base.py`** — SQLAlchemy Base metadata registry — **smoke only** — smoke tests verify import-only; no tests verify Base.metadata state, table registration mechanics, or schema evolution. Every ORM object depends on this.

- **`lib/core/interfaces.py`** — Abstract interfaces / mixins — **smoke only** — smoke test verifies import, but no test validates interface contracts or mixin behavior. Core to plugin design.

### Partially Tested (Integration Covers It)

- **`lib/database/session.py`** — ConnectionRegistry, SessionFactory, thread-local session management — **integration tested** — `test_api.py` and `test_multidb_phase1_integration.py` exercise this heavily via actual DB calls; no dedicated unit tests for registry state, session lifecycle, or error cases (e.g., connection failures).

---

## Tier 2 (Important) — 7 gaps

These affect features or enable services. Most are partially tested; a few lack dedicated coverage.

### Smoke Only (Import Not Validated Behaviorally)

- **`lib/core/interfaces.py`** — (see Tier 1, listed above for completeness)

- **`lib/services/nav.py`** — Navigation state query service — **smoke only** — companion to `navigation_service.py`, but no tests validate its read-only query contract or state consistency. Lightweight service; used in views.

- **`lib/api/server.py`** — FastAPI app factory and middleware setup — **smoke only** — smoke test only verifies it imports; no tests for app lifecycle, middleware order, startup/shutdown hooks, or CORS/headers. High leverage; affects all API calls.

- **`lib/api/router_registry.py`** — Route registration registry — **smoke only** — imports only; no tests for registry state, collisions, or lookup performance.

- **`lib/repositories/base.py`** — Abstract repository base class — **smoke only** — defines query patterns; smoke test verifies import, but no tests validate CRUD contract or transaction handling.

### Partially Tested

- **`lib/database/query.py`** — Query builder / safe query wrapper — **smoke only** — smoke test imports; no dedicated tests for query construction, SQL injection prevention, parameter binding, or result handling. Used in `user_repository.py` but tested only through repository integration tests.

- **`lib/adapters/redis_adapter.py`** — Redis cache adapter — **dedicated tests** (`test_adapters.py`, 5 tests) — but tests use an in-memory mock, not real Redis; real failures (connection loss, key expiry, data types) are not validated. Critical for caching layer.

- **`lib/security/vault_store.py`** — Encrypted vault persistence layer — **smoke only** — smoke test imports; no tests for file I/O, encryption/decryption roundtrips, or corruption handling. Tested implicitly via `test_vault_service.py`, which covers the service; store itself is untested.

---

## Tier 3 (Nice-to-have) — 27 gaps

UI components, views, and non-critical services. Smoke tests verify they load; dedicated tests cover a few; most rely on manual QA or integration tests.

### Smoke Only (No Behavior Tests)

**Core UI Infrastructure:**
- **`lib/ui/adapter.py`** — Flet page adapter — smoke only — no tests for page lifecycle or event binding.
- **`lib/ui/error_adapter.py`** — Error rendering to UI — smoke only — no tests for error format or display logic.

**View Components (not tested):**
- **`lib/ui/components/dev_nav.py`** — Developer navigation — smoke only
- **`lib/ui/components/nav_button.py`** — Navigation button — smoke only
- **`lib/ui/components/back_button.py`** — Back button — smoke only
- **`lib/ui/components/nav_bar.py`** — Top nav bar — smoke only
- **`lib/ui/components/side_bar.py`** — Side navigation — smoke only
- **`lib/ui/components/card.py`** — Generic card component — smoke only
- **`lib/ui/components/copy_button.py`** — Copy-to-clipboard button — smoke only

(All UI components are tested behaviorally only in `test_admin_tabs.py` and `test_status_card.py`; others rely on smoke tests and manual testing.)

**Views (not tested):**
- **`lib/views/home.py`** — Home page — smoke only
- **`lib/views/login.py`** — Login view — smoke only
- **`lib/views/products.py`** — Product list view — smoke only
- **`lib/views/product_detail.py`** — Product detail view — smoke only
- **`lib/views/security.py`** — Security/vault view — smoke only
- **`lib/views/vault_test.py`** — Vault testing view — smoke only
- **`lib/views/not_found.py`** — 404 view — smoke only

(All views tested via `test_router.py` smoke routes; individual view logic is not unit tested.)

**Non-Critical Services:**
- **`lib/services/connection_tester.py`** — Database connection test utility — dedicated tests (class-based in `test_connection_tester.py`); tests stub the adapters, not real DB.
- **`lib/services/cache_tester.py`** — Cache adapter test utility — dedicated tests (class-based in `test_cache_tester.py`); similar stubs.

**Models:**
- **`lib/models/user.py`** — SQLAlchemy User ORM model — smoke only — smoke test imports; no tests for model fields, relationships, or constraints.

**Config:**
- **`lib/config/settings.py`** — Environment configuration — dedicated tests (`test_settings.py`, 7 tests) — covers env var loading and database URL parsing; missing: invalid config rejection, file-based config, secrets handling.

---

## Analysis: What's Actually at Risk?

### High Risk (Tier 1)
1. **Migrations (`lib/database/migrations/env.py`)** — Auto-generated Alembic code; rarely changes; low risk in practice. *Recommendation:* Test manually on first new migration; add integration test for migration up/down cycle.

2. **Session management (`lib/database/session.py`)** — Exercised heavily via integration tests; real DB tests catch most failures. *Recommendation:* Add dedicated unit tests for registry error cases (missing connection key, thread-local cleanup).

3. **Base classes (`lib/core/interfaces.py`, `lib/repositories/base.py`)** — Structural; tested implicitly by all subclasses. *Recommendation:* Add minimal contract tests (one happy-path test per interface).

### Medium Risk (Tier 2)
1. **Redis adapter (`lib/adapters/redis_adapter.py`)** — Tests use in-memory mock. *Recommendation:* Add optional Docker-based Redis integration tests; document mock limitations in README.

2. **Server setup (`lib/api/server.py`)** — FastAPI app wiring; smoke tests verify imports. *Recommendation:* Add test for middleware stack, CORS headers, 500-error handling.

3. **Query layer (`lib/database/query.py`)** — SQL safety; tested only through repository. *Recommendation:* Add unit tests for `safe_query()` with parameterization, SQL injection attempts.

### Low Risk (Tier 3)
- UI components and views: smoke tests confirm they load; manual QA covers layout/interaction. No major risk.

---

## Test Strategy Recommendations

### Priority 1: Add Unit Tests (1–2 days)
1. `lib/database/query.py` — SQL safety validation
2. `lib/core/interfaces.py` and `lib/repositories/base.py` — Contract validation
3. `lib/api/server.py` — App setup and error handling

### Priority 2: Expand Existing Tests (1–2 days)
1. `lib/database/session.py` — Add error cases (bad connection key, cleanup)
2. `lib/adapters/redis_adapter.py` — Document mock vs. real Redis; add optional integration tests
3. `lib/security/vault_store.py` — Test file I/O and encryption directly, not just via service

### Priority 3: Nice-to-Have (1 week+)
- Individual view unit tests (low ROI; smoke tests + integration tests cover rendering)
- UI component snapshot tests (if Flet supports; currently manual)
- Config file tests (currently env var only)

---

## Notes

- **Smoke tests** (`test_smoke.py`) cover 38 modules via import-only validation. They are a safety net, not a behavior test. They confirm the app boots; they do NOT test logic.

- **Integration tests** (`test_api.py`, `test_multidb_phase1_integration.py`, `test_base_view.py`) exercise the full stack with real sessions and page objects. These implicitly test many modules (e.g., `session.py`, `router.py`, routes).

- **No test for migrations** (`env.py`) — alembic handles schema generation; we test the migrated schema implicitly via model tests. First new migration should be run locally to verify.

- **No test for model definitions** (`lib/models/user.py`) — ORM models are declarative; tested implicitly by repository and session tests. Adding dedicated tests is low ROI.

- **View and component tests** are minimal by design:
  - Views are routing + layout; tested via `test_router.py` and smoke tests.
  - Components are dumb Flet wrappers; tested only if they have logic (admin_tabs, status_card).

---

## Summary Table: Coverage by Confidence Level

| Confidence | Module Count | Coverage Type | Examples |
|------------|--------------|---------------|----------|
| **High** (dedicated + integration tests) | 12 | Behavior + integration | `navigation_service`, `user_repository`, `vault_service` |
| **Medium** (integration or comprehensive smoke) | 15 | Exercised via full stack | `session.py`, `router.py`, `base_view.py` |
| **Low** (smoke only) | 23 | Import-verified only | Views, most UI components, config |
| **Untested** | 1 | Zero coverage | `migrations/env.py` |

**Overall Assessment:** 41 of 51 modules (80%) have some coverage. Of the 10 gaps, 7 are Tier 3 (UI/views, low risk). The 3 Tier 1 gaps are either auto-generated (migrations) or exercised via integration tests (session). Recommend prioritizing Tier 2 gaps (query safety, error cases) for next sprint.
