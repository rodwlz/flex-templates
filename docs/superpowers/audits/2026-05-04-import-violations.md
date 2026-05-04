# Import Boundary Violations Audit — Phase 2 Task 2
**Date:** 2026-05-04  
**Scope:** FlexTemplates 2.0 codebase  
**Framework:** CONVENTIONS.md §6 Import Rules

---

## Summary

**Status:** VIOLATIONS FOUND (3 total)

**Circular imports:** None detected — all test imports pass cleanly.

**Pattern:** Views importing services directly (3 violations in admin views).

---

## For Sonnet Review (Design Issues)

### 0 issues

No circular imports, no architecture-breaking patterns. Views are importing services *directly* rather than via `props`, which is a design violation but not a circular dependency or load-bearing issue.

---

## For Opus Refactor (Mechanical Fixes)

### Violation 1: `AdminDatabasesView` importing `ConnectionTester` service
**File:** `lib/views/admin/databases.py:12`  
**Import:** `from lib.services.connection_tester import ConnectionTester`  
**Layer rule violated:** Section 6, Views row: "Views may import: `ui/`, `contracts/` — via `props` dict only"

**Recommended fix:**
- Remove direct import of `ConnectionTester`
- Receive `connection_tester` via `self.props.get("connection_tester")` in `build_content()`
- Wiring happens in `main.py` when instantiating the view

---

### Violation 2: `AdminCachesView` importing `CacheRegistry` service
**File:** `lib/views/admin/caches.py:9`  
**Import:** `from lib.services.cache_registry import CacheRegistry`  
**Layer rule violated:** Section 6, Views row: "Views may import: `ui/`, `contracts/` — via `props` dict only"

**Recommended fix:**
- Remove direct import of `CacheRegistry`
- Receive `cache_registry` via `self.props.get("cache_registry")` in `build_content()`
- Wiring happens in `main.py` when instantiating the view

---

### Violation 3: `AdminCachesView` importing `CacheTester` service
**File:** `lib/views/admin/caches.py:10`  
**Import:** `from lib.services.cache_tester import CacheTester`  
**Layer rule violated:** Section 6, Views row: "Views may import: `ui/`, `contracts/` — via `props` dict only"

**Recommended fix:**
- Remove direct import of `CacheTester`
- Receive `cache_tester` via `self.props.get("cache_tester")` in `build_content()`
- Wiring happens in `main.py` when instantiating the view

---

## Verification Results

### Circular import tests
All test imports completed successfully (no errors):
- ✓ `from lib.views.admin.databases import AdminDatabasesView`
- ✓ `from lib.views.admin.caches import AdminCachesView`
- ✓ `from lib.ui.error_adapter import FletErrorAdapter`
- ✓ `from lib.services.navigation_service import NavigationService`

### Layer-by-layer audit

| Layer | Rule | Status |
|-------|------|--------|
| `contracts/` | No imports from `lib/` | ✓ PASS |
| `core/` | No imports from `ui/`, `api/`, `views/`, `services/` | ✓ PASS |
| `models/` | No imports from services, views, API | ✓ PASS |
| `repositories/` | No imports from services, views, API, ui | ✓ PASS |
| `services/` | No imports from `ui/`, `views/`, `api/` | ✓ PASS |
| `adapters/` | No imports from `ui/`, `views/`, `api/` | ✓ PASS |
| `api/routes/` | No imports from `ui/`, `views/` | ✓ PASS |
| `ui/` | May import `core/`, `contracts/`, `services/` | ✓ PASS |
| `views/` | No direct service imports (must use `props` dict) | ✗ FAIL (3 violations) |
| Circular imports | None detected | ✓ PASS |

---

## Conclusion

The codebase has achieved clean layer separation in all core areas. The 3 violations are confined to view/service coupling in two admin views, which are mechanical refactoring tasks without architectural risk.

**Next step:** Assign violations 1–3 to Opus refactor task to move service injection to props-dict pattern.
