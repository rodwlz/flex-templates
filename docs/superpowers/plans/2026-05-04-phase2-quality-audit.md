# Phase 2 Quality Audit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename database registry key from "default" to "postgres", audit import boundaries, identify test coverage gaps by priority, and track documentation updates for Phase 2.5.

**Architecture:** Four sequential tasks — postgres rename (Opus), import boundary audit (Haiku), test coverage analysis (Haiku), doc debt memo (Haiku). First task is mechanical code change; remaining three are analysis/reporting that inform future work.

**Tech Stack:** Python grep, ast module for imports, pytest introspection, git.

---

## Task 1: Rename ConnectionRegistry "default" → "postgres"

**Files:**
- Modify: `main.py:115-116` (register call and get call)
- Test: `tests/test_admin_databases_view.py`, `tests/conftest.py` (verify no explicit "default" references)

### Steps

- [ ] **Step 1: Find all "default" references in ConnectionRegistry context**

Run: `grep -r "default" main.py tests/ | grep -i registry`

Expected: Find lines 115-116 in main.py where "default" appears. Tests should have none (they use fixtures).

- [ ] **Step 2: Update main.py line 115 (register call)**

File: `main.py`

Change from:
```python
ConnectionRegistry.register(url=db_url, name="default")
```

To:
```python
ConnectionRegistry.register(url=db_url, name="postgres")
```

- [ ] **Step 3: Update main.py line 116 (get call)**

File: `main.py`

Change from:
```python
user_repo = UserRepository(ConnectionRegistry.get("default"))
```

To:
```python
user_repo = UserRepository(ConnectionRegistry.get("postgres"))
```

- [ ] **Step 4: Verify no other "default" references in main.py**

Run: `grep -n '"default"' main.py`

Expected: No output (all "default" references replaced).

- [ ] **Step 5: Run all tests to verify rename doesn't break anything**

Run: `pytest tests/ -x -q`

Expected: All 244 tests pass.

- [ ] **Step 6: Verify admin databases view still works**

Run: `pytest tests/test_admin_databases_view.py -v`

Expected: All database tests pass (the view reads from ConnectionRegistry._factories which now has "postgres" instead of "default").

- [ ] **Step 7: Check for "default" in docstrings or comments**

Run: `grep -r "default.*database\|database.*default" . --include="*.py" --include="*.md" | grep -v ".git" | grep -v "test"`

Expected: Find references in docs (CONVENTIONS.md, QUICKSTART.md, etc.) mentioning "default" database, but these are OK because they're conceptual. main.py code should have no references.

- [ ] **Step 8: Commit**

```bash
git add main.py
git commit -m "refactor: rename ConnectionRegistry key 'default' → 'postgres'

- Change register() call to use name='postgres' (matches POSTGRES_URL vault key)
- Change get() call to fetch from 'postgres' instead of 'default'
- All 244 tests pass
- Aligns with CONVENTIONS.md §1 naming pattern"
```

---

## Task 2: Import Boundary Audit

**Files:**
- Create: `docs/superpowers/audits/2026-05-04-import-violations.md` (report with two sections)
- Modify: None (analysis only)

**Context:** CONVENTIONS.md §6 defines import boundaries:
- `lib/contracts/` imports pydantic only
- `lib/views/` no direct service imports (get via props)
- `lib/services/` no view imports
- `lib/api/routes/` no view imports
- No circular imports between layers

### Steps

- [ ] **Step 1: Verify contracts/ imports are clean (should be easy)**

Run: `grep -r "^from lib\|^import lib" lib/contracts/ | grep -v pydantic | grep -v "^\\."`

Expected: No output (contracts/ imports only pydantic and stdlib).

**If you find violations:** Document them in the report as "critical violations in contracts/ (should never happen)."

- [ ] **Step 2: Find views/ importing services directly**

Run: `grep -r "from lib.services import\|from lib.core.interfaces import.*Service" lib/views/`

Expected: No output (views should not import services directly).

**If you find violations:** Note the file and import statement.

- [ ] **Step 3: Find services/ importing views or ui**

Run: `grep -r "from lib.views import\|from lib.ui import" lib/services/`

Expected: No output.

**If you find violations:** Note the file and import statement. This is a design violation (services should not know about UI).

- [ ] **Step 4: Find api/routes/ importing views**

Run: `grep -r "from lib.views import" lib/api/routes/`

Expected: No output.

**If you find violations:** Note them. Routes should not import views directly.

- [ ] **Step 5: Find contracts/ importing from lib outside pydantic**

Run: `grep -r "^from lib\." lib/contracts/ | grep -v "# noqa"`

Expected: No output (or only false positives in comments).

**If you find violations:** These are critical — contracts/ is the most isolated layer.

- [ ] **Step 6: Spot-check complex areas for circular imports**

Run each:
```bash
python -c "from lib.views.admin.databases import AdminDatabasesView" && echo "admin/databases: OK"
python -c "from lib.views.admin.caches import AdminCachesView" && echo "admin/caches: OK"
python -c "from lib.ui.error_adapter import FletErrorAdapter" && echo "error_adapter: OK"
python -c "from lib.services.navigation_service import NavigationService" && echo "nav_service: OK"
```

Expected: All OK (no circular import errors).

**If any fail:** Note the circular import in the report.

- [ ] **Step 7: Create report file with two sections**

Create: `docs/superpowers/audits/2026-05-04-import-violations.md`

```markdown
# Import Boundary Audit — 2026-05-04

## Status

**Total violations found:** [COUNT]

---

## For Sonnet Review (Design Issues)

These imports violate architectural layers and suggest tighter coupling than intended. Sonnet assesses each and recommends refactor approach.

### Violations

[List violations that require design decisions — e.g., circular imports, services importing views, etc.]

Example format:
- **File:** `lib/services/user_service.py:5`
  **Issue:** `from lib.views.admin import something`
  **Problem:** Services should not know about views (violates CONVENTIONS.md §6)
  **Recommendation:** Move shared logic to contracts or core

---

## For Opus Refactor (Mechanical Fixes)

These imports are straightforward reorganization (e.g., wrong layer importing from wrong layer). Opus fixes with import reorganization.

### Violations

[List violations that are mechanical fixes — wrong import paths, reorganization only.]

Example format:
- **File:** `lib/api/routes/users.py:3`
  **Issue:** `from lib.api.routes.helpers import format_user` (should be relative import)
  **Fix:** Change to `from .helpers import format_user`

---

## Summary

- Contracts layer: ✅ Clean
- Views layer: [PASS/FAIL]
- Services layer: [PASS/FAIL]
- API layer: [PASS/FAIL]
- No circular imports: [PASS/FAIL]
```

- [ ] **Step 8: Review your violations list**

Read through the violations you found. Make sure each one is either:
- A **design issue** (requires Sonnet's judgment on refactor approach), OR
- A **mechanical fix** (straightforward reorganization)

If a violation is unclear, put it in "For Sonnet Review" and let Sonnet decide.

- [ ] **Step 9: Commit the audit report**

```bash
git add docs/superpowers/audits/2026-05-04-import-violations.md
git commit -m "audit: import boundary violations report

- Audited lib/contracts/, lib/views/, lib/services/, lib/api/ for boundary violations
- Verified no circular imports in complex areas
- Violations categorized: [N] for Sonnet review (design), [M] for Opus refactor (mechanical)
- See report for details and recommended fixes"
```

---

## Task 3: Test Coverage Gaps (Prioritized Analysis)

**Files:**
- Create: `docs/superpowers/audits/2026-05-04-test-coverage-gaps.md` (list of gaps by tier)
- Modify: None (analysis only)

### Steps

- [ ] **Step 1: List all .py files in lib/**

Run: `find lib -name "*.py" -not -name "__*" | sort`

Expected: Complete inventory of all modules (no `.pyc`, no `__pycache__`).

- [ ] **Step 2: Check which have corresponding test files**

For each file from Step 1, check if `tests/test_<module>.py` or `tests/test_<parent>/<submodule>.py` exists.

Example:
- `lib/adapters/redis_adapter.py` → `tests/test_adapters.py` ✅
- `lib/api/server.py` → `tests/test_api_server.py` ❌ (gap)

Create a spreadsheet/list: [module] → [test exists? Y/N]

- [ ] **Step 3: Identify gaps and group by layer**

Layers (in order):
1. **core/** (interfaces, events, patterns) — most foundational
2. **config/** (settings, vault initialization)
3. **contracts/** (data models) — should be simple
4. **database/** (session factory, uow) — critical for data layer
5. **models/** (ORM definitions)
6. **repositories/** (data access)
7. **services/** (business logic)
8. **api/** (HTTP layer)
9. **ui/** (Flet components and layout)
10. **views/** (page modules)
11. **adapters/** (non-SQL backends)

For each gap, note:
- Module name and purpose (one sentence)
- Why it's untested
- Tier (see Step 4)

- [ ] **Step 4: Rank gaps by criticality**

Assign tier:

**Tier 1 (Critical):**
- Core infrastructure: `lib/core/interfaces.py`, `lib/core/events.py`, `lib/database/session.py`
- Base classes used by everything: `lib/repositories/base.py`
- Foundational services: `lib/services/navigation_service.py` (already tested ✓)

**Tier 2 (Important):**
- Data layer: `lib/database/uow.py`, any repository without tests
- API infrastructure: `lib/api/server.py`, `lib/api/router_registry.py`
- Services: any `*_service.py` without tests
- Configuration: `lib/config/settings.py` (already tested ✓)

**Tier 3 (Nice-to-Have):**
- UI components: `lib/ui/components/*.py` (visual, harder to test)
- Views: individual view files
- Adapters: file adapter, non-critical adapters

Example gap:
```
### Tier 1 (Critical)
- **lib/api/server.py** — BackendServer lifecycle (start/stop) — Untested — Critical for API reliability

### Tier 2 (Important)
- **lib/ui/error_adapter.py** — FletErrorAdapter (snackbar/fatal dialogs) — Untested — Important for error UX

### Tier 3 (Nice-to-Have)
- **lib/ui/components/nav_bar.py** — NavBar rendering — Partial (tests exist but incomplete) — Visual component
```

- [ ] **Step 5: Create markdown report**

File: `docs/superpowers/audits/2026-05-04-test-coverage-gaps.md`

```markdown
# Test Coverage Gaps — 2026-05-04

## Summary

- **Total modules:** [N]
- **Tested:** [M]
- **Gaps:** [N-M]
- **Coverage:** [M/(N)*100]%

---

## Tier 1 (Critical) — [COUNT] gaps

[List gaps with one-line purpose and why untested]

Examples:
- **lib/api/server.py** — BackendServer (start/stop/shutdown) — Untested — Daemon thread lifecycle needs coverage
- **lib/ui/error_adapter.py** — FletErrorAdapter (snackbar + fatal dialogs) — Untested — Error UX is user-facing

---

## Tier 2 (Important) — [COUNT] gaps

[List gaps]

---

## Tier 3 (Nice-to-Have) — [COUNT] gaps

[List gaps]

---

## Notes

- Smoke tests (56 tests) cover import chains but not functional behavior
- Some modules have partial test coverage (e.g., nav_bar tested as component, not in isolation)
- Tier assignments reflect: Tier 1 = breaks app if wrong, Tier 2 = affects feature, Tier 3 = nice polish
```

- [ ] **Step 6: Review your list for completeness**

Go through the gaps list. Make sure:
- Every untested module is listed (no false negatives)
- Tier assignments make sense (you can explain why each tier matters)
- Purposes are one sentence and clear

- [ ] **Step 7: Commit the gaps report**

```bash
git add docs/superpowers/audits/2026-05-04-test-coverage-gaps.md
git commit -m "audit: test coverage gaps report

- Inventoried all modules in lib/ (~[N] total)
- Identified [M] gaps across [N-M] untested modules
- Prioritized by tier: [T1] critical, [T2] important, [T3] nice-to-have
- See report for modules, purposes, and tier justification
- Ready for Sonnet prioritization and Opus implementation"
```

---

## Task 4: Doc Debt Memo (Phase 2.5 Tracking)

**Files:**
- Create: `docs/superpowers/audits/2026-05-04-doc-updates-phase2.5.md` (memo)
- Modify: None (tracking only)

### Steps

- [ ] **Step 1: Review DI_GUIDE.md**

File: `docs/DI_GUIDE.md`

Read the full file (scanning for sections that don't match current code).

Expected findings:
- Mentions of `Container` class (doesn't exist in code — direct wiring in main.py instead)
- Examples showing DI container setup (aspirational)
- References to `@inject` decorator pattern (real pattern is `props` dict in views)

**Document:**
- What's aspirational vs real
- What needs updating
- Estimated effort (few sentences)

- [ ] **Step 2: Review CONTRACTS_GUIDE.md**

File: `docs/CONTRACTS_GUIDE.md`

Skim for:
- Mentions of `UserService` (aspirational, not in codebase)
- `flex_app/` vs `lib/` naming (should be mostly fixed from bulk replace)
- Contract examples — do they match actual code patterns?

**Document:**
- What's outdated
- What examples need updating
- Estimated effort

- [ ] **Step 3: Review PONG_EXAMPLE.md**

File: `docs/PONG_EXAMPLE.md`

Check:
- Import paths (should be `lib.games`, not `flex_app.games`)
- Adapter patterns match actual code
- Engine/state patterns align with current code

**Document:**
- What needs updating
- Estimated effort

- [ ] **Step 4: Create memo file**

File: `docs/superpowers/audits/2026-05-04-doc-updates-phase2.5.md`

```markdown
# Documentation Updates — Phase 2.5 Tracking

**Status:** Deferred. These updates don't block Phase 2 (code is correct, docs are aspirational).

---

## DI_GUIDE.md

**Current state:** Describes `Container` class from `dependency-injector` library; examples show DI container setup.

**Reality:** Code uses direct wiring in `main.py` (no container). Services are injected into views via `props` dict, not via DI container.

**What needs fixing:**
1. Remove/rewrite Section "The DI Container" — replace examples showing Container class with actual main.py pattern
2. Update code examples: show `props["nav_service"]` in views instead of `@inject` decorator
3. Keep conceptual sections (what is DI, why it matters) — they're still correct

**Effort:** ~1-2 hours. High impact (clarifies architecture).

---

## CONTRACTS_GUIDE.md

**Current state:** Examples mention `UserService` class (aspirational, not in current code). Some flex_app naming (mostly fixed).

**Reality:** Code has `NavigationService`, `VaultService`, `SchemaInspector`, `ConnectionTester`, etc. but not `UserService`.

**What needs fixing:**
1. Replace `UserService` examples with real service examples (NavigationService or VaultService)
2. Double-check all import paths use `lib.` not `flex_app.`
3. Verify contract flow examples match actual code

**Effort:** ~1 hour. Medium impact (examples clarity).

---

## PONG_EXAMPLE.md

**Current state:** Import paths may still reference old naming. Engine/adapter patterns should be correct.

**Reality:** Code is in `lib/games/` not `flex_app/games/`. Patterns are solid.

**What needs fixing:**
1. Verify all import paths use `lib.games` not `flex_app.games`
2. Spot-check adapter examples against actual keyboard_adapter.py / mock_neural_adapter.py
3. Verify engine/state patterns match games/engine.py

**Effort:** ~30 minutes. Low-medium impact (completeness).

---

## Summary

- **Total doc updates needed:** 3 files
- **Estimated effort:** 2.5-3.5 hours total (1 person)
- **Priority:** After Sonnet reviews import audit and test gaps (Phase 2.5)
- **Owner:** Haiku can write, Sonnet can review, Opus implements

Not blocking Phase 2 completion.
```

- [ ] **Step 5: Commit the memo**

```bash
git add docs/superpowers/audits/2026-05-04-doc-updates-phase2.5.md
git commit -m "track: documentation updates for Phase 2.5

- DI_GUIDE: Container class aspirational, needs rewrite to match actual main.py wiring
- CONTRACTS_GUIDE: UserService examples need replacement with real services
- PONG_EXAMPLE: Import paths should be verified/updated
- Deferred: Not blocking Phase 2 (code is correct, docs are just aspirational)
- See memo for details and effort estimates"
```

---

## Success Criteria (Phase 2 Complete)

✅ All 244 tests pass (postgres rename doesn't break anything)  
✅ Import boundary audit complete (violations report created, categorized)  
✅ Test coverage gaps identified and prioritized (Sonnet-ready list created)  
✅ Doc debt tracked (Phase 2.5 memo created, deferred)
