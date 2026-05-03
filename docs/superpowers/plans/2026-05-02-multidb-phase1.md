# Phase 1: Multi-Database Connection Manager + Schema Viewer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only database inspector that connects to multiple databases (from `.env`), shows connection status, and lets users view tables and schema.

**Architecture:** Extend `AppConfig` to load `DATABASE_*` env vars, register them in `ConnectionRegistry`, build two services (`SchemaInspector` and `ConnectionTester`) using SQLAlchemy's `inspect()` API, wire them into a Flet dashboard view. All boilerplate follows existing FlexTemplates patterns (SimpleService, contracts, error handling).

**Tech Stack:** SQLAlchemy 2.0 introspection, Pydantic, Flet, pytest, existing FlexTemplates DI/contracts.

---

## File Map

**Modify:**
- `lib/config/settings.py` — add `databases` field
- `main.py` — load and register databases

**Create:**
- `lib/services/schema_inspector.py` — SQLAlchemy reflection service
- `lib/services/connection_tester.py` — connectivity test service
- `lib/views/admin/__init__.py` — empty
- `lib/views/admin/databases.py` — dashboard UI
- `tests/test_schema_inspector.py` — unit tests
- `tests/test_connection_tester.py` — unit tests
- `tests/test_admin_databases_view.py` — view tests
- `tests/test_multidb_phase1_integration.py` — end-to-end test

**Update:**
- `tests/test_smoke.py` — add new module imports

---

## Tasks

### Task 1: Extend AppConfig to load DATABASE_* env vars

**Files:**
- Modify: `lib/config/settings.py`

- [ ] **Step 1: Read the current AppConfig class**

Open `lib/config/settings.py` and review the existing fields.

- [ ] **Step 2: Add databases field to AppConfig**

Add to the AppConfig class:
```python
databases: dict[str, str] = {}
```

And in `__init__`, auto-populate from env vars with DATABASE_ prefix.

- [ ] **Step 3: Test AppConfig loads DATABASE_* vars**

Test with `export DATABASE_MAIN=postgresql://localhost/test_db` etc.

- [ ] **Step 4: Commit**

```bash
git add lib/config/settings.py
git commit -m "feat: extend AppConfig to load DATABASE_* env vars"
```

---

### Task 2: Build SchemaInspector service (tests first)

**Files:**
- Create: `lib/services/schema_inspector.py`
- Create: `tests/test_schema_inspector.py`

- [ ] **Step 1: Write failing tests for SchemaInspector**

Create `tests/test_schema_inspector.py` with tests:
- `test_get_tables_returns_table_list()`
- `test_get_schema_returns_columns_and_types()`
- `test_get_schema_handles_missing_table()`
- `test_get_schema_requires_table_name()`

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_schema_inspector.py -v
```

- [ ] **Step 3: Create SchemaInspector service**

Implement `lib/services/schema_inspector.py` with:
- `get_tables(data)` — uses SQLAlchemy `inspect()` to list tables
- `get_schema(data)` — fetches columns, types, constraints for a table

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_schema_inspector.py -v
```

- [ ] **Step 5: Commit**

```bash
git add lib/services/schema_inspector.py tests/test_schema_inspector.py
git commit -m "feat: add SchemaInspector service with SQLAlchemy reflection"
```

---

### Task 3: Build ConnectionTester service (tests first)

**Files:**
- Create: `lib/services/connection_tester.py`
- Create: `tests/test_connection_tester.py`

- [ ] **Step 1: Write failing tests for ConnectionTester**

Create `tests/test_connection_tester.py` with tests:
- `test_test_returns_alive_true_on_working_connection()`
- `test_test_handles_connection_failure()`
- `test_test_never_raises_exception()`

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_connection_tester.py -v
```

- [ ] **Step 3: Create ConnectionTester service**

Implement `lib/services/connection_tester.py` with:
- `test(data)` — runs SELECT 1, catches all exceptions, returns `{alive: bool, error: str | None, latency_ms: float}`

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_connection_tester.py -v
```

- [ ] **Step 5: Commit**

```bash
git add lib/services/connection_tester.py tests/test_connection_tester.py
git commit -m "feat: add ConnectionTester service with error handling"
```

---

### Task 4: Build admin dashboard view

**Files:**
- Create: `lib/views/admin/__init__.py`
- Create: `lib/views/admin/databases.py`
- Create: `tests/test_admin_databases_view.py`

- [ ] **Step 1: Create admin views directory**

```bash
mkdir -p lib/views/admin && touch lib/views/admin/__init__.py
```

- [ ] **Step 2: Write failing tests for dashboard view**

Create `tests/test_admin_databases_view.py` with tests:
- `test_view_renders_without_crashing()`
- `test_view_displays_database_list()`

- [ ] **Step 3: Run tests to verify they fail**

```bash
python -m pytest tests/test_admin_databases_view.py -v
```

- [ ] **Step 4: Create AdminDatabasesView**

Implement `lib/views/admin/databases.py`:
- Extends BaseView
- Displays list of databases from config
- Shows connection status for each
- Has `view(page, props)` entry point

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_admin_databases_view.py -v
```

- [ ] **Step 6: Commit**

```bash
git add lib/views/admin/__init__.py lib/views/admin/databases.py tests/test_admin_databases_view.py
git commit -m "feat: add admin database inspector view"
```

---

### Task 5: Write integration test (end-to-end)

**Files:**
- Create: `tests/test_multidb_phase1_integration.py`

- [ ] **Step 1: Create integration test file**

Create `tests/test_multidb_phase1_integration.py` with:
- Setup fixture that creates two in-memory SQLite databases with sample tables
- `test_full_workflow_connection_to_schema()` that:
  - Registers both DBs
  - Tests both connections are alive
  - Inspects main DB tables
  - Gets schema for a specific table

- [ ] **Step 2: Run integration test**

```bash
python -m pytest tests/test_multidb_phase1_integration.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_multidb_phase1_integration.py
git commit -m "test: add Phase 1 integration test (full workflow)"
```

---

### Task 6: Update smoke tests

**Files:**
- Modify: `tests/test_smoke.py`

- [ ] **Step 1: Add new module imports to smoke tests**

In the `@pytest.mark.parametrize("module_path", ...)` list, add:
- `"lib.config.settings"`
- `"lib.services.schema_inspector"`
- `"lib.services.connection_tester"`
- `"lib.views.admin.databases"`

- [ ] **Step 2: Run smoke tests**

```bash
python -m pytest tests/test_smoke.py::test_module_imports_cleanly -v
```

- [ ] **Step 3: Run full test suite to verify nothing broke**

```bash
python -m pytest tests/ -q
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: add Phase 1 modules to smoke tests"
```

---

### Task 7: Wire databases into main.py

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update main.py to load and register databases**

After `config = AppConfig()`, add:
```python
for db_name, db_url in config.databases.items():
    try:
        ConnectionRegistry.register(url=db_url, name=db_name)
    except Exception as e:
        print(f"Warning: Failed to register database '{db_name}': {e}")
```

- [ ] **Step 2: Register the admin/databases route**

In the router setup, add:
```python
router.register("/admin/databases", "lib.views.admin.databases")
```

- [ ] **Step 3: Add config to props_factory**

In `set_props_factory`, add:
```python
"config": config,
```

- [ ] **Step 4: Test main.py imports**

```bash
export DATABASE_MAIN=sqlite:///./dev.db
python -c "from main import main; print('✓ main.py imports and loads databases')"
```

- [ ] **Step 5: Run full test suite**

```bash
python -m pytest tests/ -q
```

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat: wire Phase 1 databases into main.py"
```

---

## Success Criteria

- [ ] All 7 tasks complete with passing tests
- [ ] All ~185+ existing tests still pass
- [ ] New modules are importable in smoke tests
- [ ] Main.py wires databases and admin view
- [ ] Code follows FlexTemplates patterns (SimpleService, contracts, error handling)
- [ ] Ready for Sonnet review and refinement
