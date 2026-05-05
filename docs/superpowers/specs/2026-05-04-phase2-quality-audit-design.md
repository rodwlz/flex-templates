# Phase 2 Quality Audit — Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create the implementation plan once this spec is approved.

**Goal:** Refactor registry naming to match conventions, verify import boundaries are clean, identify test coverage gaps, and track documentation debt.

**Architecture:** Four independent tasks executed in sequence — postgres rename (mechanical), import audit (verification), test gaps (analysis), doc tracking (memo). Code work first; docs deferred.

**Tech Stack:** Python grep/ast analysis, pytest introspection, git diffs.

---

## Task 1: Rename "default" → "postgres"

**Problem:** ConnectionRegistry key `"default"` is generic. CONVENTIONS.md establishes that vault keys map to registry names: `POSTGRES_URL` → `"postgres"`, `DATABASE_*` → lowercase names. Using `"default"` breaks this pattern.

**Solution:** Rename the registry key throughout the codebase.

**Scope:**
- `main.py` line 116: `ConnectionRegistry.get("default")` → `get("postgres")`
- All test fixtures that register the default database
- Comments/docstrings that reference the key

**Success criteria:**
- All tests pass (244/244)
- No remaining references to `ConnectionRegistry.get("default")`
- CONVENTIONS.md §1 and main.py are in sync

**Owner:** Opus (mechanical refactor, straightforward)

---

## Task 2: Import Boundary Audit

**Problem:** Code should follow CONVENTIONS.md §6 import rules, but violations may have accumulated (especially in views, api routes, services).

**Solution:** Grep entire codebase for import violations; categorize by type (design issue vs mechanical fix).

**Boundaries to verify:**
- `lib/contracts/` imports only `pydantic` and stdlib
- `lib/views/` never import services directly (receive via props dict)
- `lib/services/` never import views or ui
- `lib/api/routes/` never import views
- Each layer respects its tier (no downward leaks, no circular imports)

**Method:**
1. Audit `lib/contracts/` imports (should be clean) — verify once
2. Grep `from lib.services import` in `lib/views/` → flag violations
3. Grep `from lib.ui import` in `lib/services/` → flag violations
4. Grep `from lib.views import` in `lib/api/` → flag violations
5. Grep `from lib.* import` in `lib/contracts/` for non-pydantic imports → flag violations
6. Spot-check known complex areas (admin views, error_adapter, navigation)

**Output:** Two lists:
- **For Sonnet review:** Imports that suggest architectural issues (e.g., circular imports, tight coupling between layers). Sonnet assesses design and recommends refactor approach.
- **For Opus refactor:** Mechanical violations (e.g., wrong layer importing from wrong layer). Opus fixes with straightforward reorganization.

**Success criteria:**
- All imports audited (no false negatives)
- Each violation categorized with rationale
- CONVENTIONS.md §6 fully satisfied after fixes

**Owner:** Haiku audits (grep + categorize); Sonnet reviews (design); Opus refactors (code)

---

## Task 3: Test Coverage Gaps (Prioritized List)

**Problem:** 244 tests exist, but coverage is uneven. Some critical modules untested; some gaps are nice-to-have.

**Solution:** Audit all modules in `lib/`; identify gaps; rank by importance.

**Method:**
1. List all `.py` files in `lib/` (excluding `__init__.py`, `*.pyc`)
2. For each, check if `tests/test_<module>.py` or `tests/test_<parent>/<module>.py` exists
3. If no test file, list as gap with module tier (core, data, service, ui, api)
4. Rank gaps:
   - **Tier 1 (critical):** Core infrastructure (`interfaces.py`, `events.py`, `session.py`), base classes (`base.py` in all tiers)
   - **Tier 2 (important):** Data layer (`repositories/`, `uow.py`), services (`*_service.py`), API infrastructure (`server.py`)
   - **Tier 3 (nice-to-have):** UI components, admin views, file adapters, example code

**Output:** Markdown list with module name, purpose, gap reason, and tier. Example:
```
### Tier 1 (Critical)
- `lib/api/server.py` — BackendServer lifecycle (start/stop) — untested — Needed for API reliability

### Tier 2 (Important)
- `lib/ui/error_adapter.py` — FletErrorAdapter (snackbar/fatal dialogs) — untested — Affects error UX

### Tier 3 (Nice-to-Have)
- `lib/ui/components/nav_bar.py` — NavBar rendering — partial (only stub tests) — Visual component
```

**Success criteria:**
- All modules inventoried (no gaps in the gap list)
- Tiers are defensible (can explain why each tier matters)
- Sonnet can use this to prioritize test implementation

**Owner:** Haiku audits (inventory + tier); Sonnet reviews (priority); Opus implements (if approved)

---

## Task 4: Doc Debt Tracking

**Problem:** DI_GUIDE, CONTRACTS_GUIDE, PONG_EXAMPLE have aspirational content (Container class, UserService) that doesn't match current code. Rather than fix now, track for Phase 2.5.

**Solution:** Create a single memo documenting what needs updates.

**Docs to track:**
- **DI_GUIDE.md** — Remove/rewrite examples showing `Container` class (doesn't exist). Show actual direct-wiring pattern from main.py instead. ~100 lines.
- **CONTRACTS_GUIDE.md** — Check for flex_app→lib naming issues (mostly fixed in bulk replace). Update any remaining aspirational UserService examples. ~50 lines.
- **PONG_EXAMPLE.md** — Verify import paths match current structure. Update if needed. ~20 lines.

**Output:** Markdown memo in `docs/superpowers/specs/` listing each doc, what needs fixing, and estimated effort.

**Success criteria:**
- Memo is clear enough that Sonnet can implement updates in Phase 2.5
- No placeholders or vagueness
- Deferral is explicit (not on Phase 2 critical path)

**Owner:** Haiku creates memo; deferred implementation

---

## Execution Order

1. **Postgres rename** (Opus) → all tests pass
2. **Import audit** (Haiku + Sonnet + Opus) → violations fixed
3. **Test coverage audit** (Haiku + Sonnet) → gaps list delivered
4. **Doc memo** (Haiku) → deferred updates tracked

---

## Success Criteria (Phase 2 Complete)

- ✅ All 244 tests pass (postgres rename + import refactors don't break anything)
- ✅ No import boundary violations remain (CONVENTIONS.md §6 fully satisfied)
- ✅ Test coverage gaps identified and prioritized (Sonnet decides next steps)
- ✅ Doc debt memo created (Phase 2.5 work is clear)
