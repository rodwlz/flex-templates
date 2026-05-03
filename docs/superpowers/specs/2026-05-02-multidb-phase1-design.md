# Phase 1: Multi-Database Connection Manager + Schema Viewer

**Date:** 2026-05-02  
**Status:** Design approved  
**Phase:** 1 of 3 (Connection Mgmt → Query Engine → Migrations)

---

## Overview

Phase 1 builds the **foundation for a generic database abstraction tool**. Users can:
- View all connected databases (from `.env`)
- See connection status (🟢 alive / 🔴 down)
- Inspect tables and schema for each database
- Test connectivity (verify permissions work)

This is read-only inspection; Phase 2 adds mutation/query logic.

---

## Architecture

```
.env (DATABASE_* connection strings)
  ↓
AppConfig (parses & validates)
  ↓
ConnectionRegistry (registers named SessionFactory per DB)
  ↓
SchemaInspector (SQLAlchemy reflect → metadata)
  ↓
ConnectionTester (SELECT 1 + sample query)
  ↓
Dashboard View (Flet UI: DBs → Tables → Schema)
```

**Key principle:** Lean on SQLAlchemy's `inspect()` API for dialect-agnostic schema introspection. Minimal custom introspection logic.

---

## Components

### 1. AppConfig Extension

**File:** `lib/config/settings.py` (modify)

Add new field:
```python
class AppConfig(BaseSettings):
    # ... existing fields ...
    
    # Phase 1: Multi-database connections
    # Format: DATABASE_MAIN=postgresql://user:pass@host/db
    #         DATABASE_ANALYTICS=postgresql://...
    #         DATABASE_CACHE_REDIS=redis://...
    # Prefix "DATABASE_" signals a connection to register.
    databases: dict[str, str] = {}  # auto-populated from env
```

Load all `DATABASE_*` env vars into this dict at startup.

### 2. SchemaInspector Service

**File:** `lib/services/schema_inspector.py` (new)

```python
class SchemaInspector(SimpleService):
    """Introspect database schema using SQLAlchemy reflection."""
    
    def get_tables(self, data: dict) -> dict:
        """
        Fetch all tables in a database.
        
        Input: {"db_name": "main"}
        Output: {
            "tables": ["customers", "orders", "products"],
            "error": null
        }
        """
        
    def get_schema(self, data: dict) -> dict:
        """
        Fetch columns, types, constraints for a specific table.
        
        Input: {"db_name": "main", "table_name": "customers"}
        Output: {
            "table": "customers",
            "columns": [
                {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                {"name": "email", "type": "VARCHAR(255)", "nullable": False, "unique": True},
                {"name": "created_at", "type": "TIMESTAMP", "nullable": True, "default": "now()"}
            ],
            "error": null
        }
        """
        
    def _inspect(self, factory: SessionFactory):
        """Use SQLAlchemy inspect() to reflect schema."""
        # Implementation uses sqlalchemy.inspect(factory._engine)
```

**Extends:** `SimpleService` (standard ActionRequest/ActionResult contract)  
**Depends on:** `ConnectionRegistry`, `SessionFactory`  
**Uses:** `sqlalchemy.inspect()` for dialect-agnostic introspection

### 3. ConnectionTester Service

**File:** `lib/services/connection_tester.py` (new)

```python
class ConnectionTester(SimpleService):
    """Test database connectivity and permissions."""
    
    def test(self, data: dict) -> dict:
        """
        Test if a connection is alive and accessible.
        
        Input: {"db_name": "main"}
        Output: {
            "db_name": "main",
            "alive": True,
            "latency_ms": 12.5,
            "error": null
        }
        
        On failure:
        Output: {
            "db_name": "main",
            "alive": False,
            "latency_ms": null,
            "error": "connection refused"
        }
        """
        
    def _test_connection(self, factory: SessionFactory) -> (bool, str | None):
        """
        1. Run SELECT 1 to verify connection
        2. Run SELECT 1 from first table to verify read permissions
        3. Return (alive, error_msg)
        """
```

**Extends:** `SimpleService`  
**Depends on:** `ConnectionRegistry`, `SessionFactory`  
**Behavior:** Catches all exceptions, returns `alive=False` with error message (never crashes)

### 4. Dashboard View

**File:** `lib/views/admin/databases.py` (new)

**Layout:**

```
┌─────────────────────────────────────────┐
│  Connected Databases                    │
├─────────────────────────────────────────┤
│ Database         Status    Tables       │
│ ────────────────────────────────────    │
│ main             🟢 live   12 tables    │
│ analytics        🔴 down   —            │
│ cache_redis      🟢 live   —            │
│                                          │
│ Click to expand and view schema         │
├─────────────────────────────────────────┤
│ Selected: main                           │
│                                          │
│ Tables:                                  │
│ • customers (15 columns)                │
│   ├─ id (INTEGER, PK)                  │
│   ├─ email (VARCHAR, UNIQUE)           │
│   └─ created_at (TIMESTAMP)            │
│ • orders (8 columns)                    │
│   ├─ id (INTEGER, PK)                  │
│   └─ ...                               │
└─────────────────────────────────────────┘
```

**Functionality:**
- List all registered DBs (from `ConnectionRegistry`)
- Show status for each (via `ConnectionTester.test()`)
- Click DB to expand and show tables (via `SchemaInspector.get_tables()`)
- Click table to show full schema (via `SchemaInspector.get_schema()`)
- Auto-refresh status every 30s (poll in background)

**Interaction flow:**
1. View loads → calls `ConnectionTester.test()` for each registered DB
2. Updates UI with status badges (🟢/🔴)
3. User clicks DB → calls `SchemaInspector.get_tables()`
4. User clicks table → calls `SchemaInspector.get_schema()`
5. Displays columns, types, constraints in a readable table

---

## Data Flow

```
1. App startup:
   AppConfig loads DATABASE_* from .env
   ConnectionRegistry.register() for each
   
2. Dashboard view mounts:
   For each registered DB:
     ConnectionTester.test(db_name) → alive/error
   Display status badges (🟢 or 🔴)
   
3. User clicks a database:
   SchemaInspector.get_tables(db_name) → table list
   Expand and show tables
   
4. User clicks a table:
   SchemaInspector.get_schema(db_name, table_name) → columns/types
   Display schema in formatted table
```

---

## Error Handling

**Philosophy:** Read-only inspection. Never crash; always return results or errors gracefully.

- **Connection fails:** `ConnectionTester` catches exception, returns `{alive: False, error: "..."}`
- **Schema introspection fails:** `SchemaInspector` catches exception, returns `{error: "cannot introspect table X"}`
- **DB goes down while viewing:** Dashboard shows 🔴 on next refresh, user is notified but view doesn't crash
- **Invalid DB name:** `SchemaInspector.get_tables()` returns `{error: "db not registered"}`

All errors surface as `ActionResult(success=False, error=...)` per the contract.

---

## Testing Strategy

### Unit Tests

**`tests/test_schema_inspector.py`**
- Mock `SessionFactory` with in-memory SQLite containing sample tables
- `test_get_tables_returns_all_tables()` → verify table list
- `test_get_schema_returns_columns_and_types()` → verify columns, types, constraints
- `test_get_schema_handles_missing_table()` → error case
- `test_get_schema_handles_missing_db()` → error case

**`tests/test_connection_tester.py`**
- Mock `SessionFactory` that succeeds/fails
- `test_test_alive_on_working_connection()` → `alive=True`
- `test_test_fails_on_down_connection()` → `alive=False, error=...`
- `test_test_never_raises_exception()` → all errors caught

**`tests/test_admin_databases_view.py`**
- Mock `SchemaInspector` and `ConnectionTester` services
- `test_view_renders_database_list()` → verify UI structure
- `test_clicking_db_loads_tables()` → verify `SchemaInspector.get_tables()` called
- `test_clicking_table_loads_schema()` → verify `SchemaInspector.get_schema()` called
- `test_status_badges_show_connection_state()` → 🟢 vs 🔴

### Integration Tests

**`tests/test_multidb_phase1_integration.py`**
- Real in-memory SQLite databases (separate)
- Register multiple named connections to `ConnectionRegistry`
- Full flow: view dashboard → click DB → expand tables → view schema
- Verify all services work together

---

## Implementation Order

1. **AppConfig** — extend to load `DATABASE_*` vars
2. **ConnectionRegistry** — verify multi-DB registration works
3. **SchemaInspector** — implement using SQLAlchemy `inspect()`
4. **ConnectionTester** — implement with error handling
5. **Dashboard View** — wire all services together
6. **Tests** — unit + integration

Each step is incremental and testable.

---

## Files to Create / Modify

| File | Action | Notes |
|---|---|---|
| `lib/config/settings.py` | Modify | Add `databases: dict[str, str]` field |
| `lib/services/schema_inspector.py` | Create | `SchemaInspector(SimpleService)` |
| `lib/services/connection_tester.py` | Create | `ConnectionTester(SimpleService)` |
| `lib/views/admin/__init__.py` | Create | empty |
| `lib/views/admin/databases.py` | Create | Dashboard view |
| `tests/test_schema_inspector.py` | Create | Unit tests |
| `tests/test_connection_tester.py` | Create | Unit tests |
| `tests/test_admin_databases_view.py` | Create | UI tests |
| `tests/test_multidb_phase1_integration.py` | Create | Integration tests |
| `tests/test_smoke.py` | Modify | Add new module imports |
| `main.py` | Modify | Load `config.databases`, register in `ConnectionRegistry` |

---

## Deliverables

- ✓ Connection manager (reads `.env`, registers to `ConnectionRegistry`)
- ✓ Schema viewer (tables + columns + types via SQLAlchemy)
- ✓ Connection tester (verify DB is alive + permissions work)
- ✓ Dashboard UI (list DBs, show status, inspect schema)
- ✓ Full test coverage (unit + integration)
- ✓ Boilerplate for Phase 2 (services, views, testing patterns established)

---

## Phase 2 Foundation

Phase 1 leaves these abstractions ready for Phase 2:
- `SchemaInspector` → can be extended to include data inspection
- `ConnectionTester` → can be extended to verify specific permissions (read, write, create)
- Services + view structure → can be cloned for query execution engine
- Test patterns → reusable for all future phases

---

## Success Criteria

- [ ] All 171 existing tests still pass
- [ ] Dashboard view renders and shows DB status
- [ ] Click to expand tables and view schema
- [ ] Connection status updates every 30s
- [ ] All new tests pass (unit + integration)
- [ ] Error handling never crashes the view
