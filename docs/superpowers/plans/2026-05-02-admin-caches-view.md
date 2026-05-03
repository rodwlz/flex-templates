# Admin Caches View — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `/admin/caches` — a live status dashboard for cache/key-value services (Redis, Memcached, etc.) that auto-discovers instances from the vault using the `SERVICE_URL` / `SERVICE_URL_ID` convention.

**Architecture:** The vault is the single source of truth for cache connections. Keys follow `{SERVICE}_URL` or `{SERVICE}_URL_{ID}` (e.g. `REDIS_URL`, `REDIS_URL_MAIN`, `REDIS_URL_ANALYTICS`). At startup `main.py` scans these keys, constructs named adapters, and registers them in a new `CacheRegistry`. The view reads `CacheRegistry` — same pattern as `ConnectionRegistry` for SQL.

**Tech Stack:** Flet, `redis-py`, existing `RedisAdapter(SimpleService)`, pytest, FlexTemplates DI/contracts.

**Vault convention (no code changes needed to add a new instance):**

| Vault key | Registered name | Service |
|---|---|---|
| `REDIS_URL` | `redis` | Redis (default) |
| `REDIS_URL_MAIN` | `redis_main` | Redis named "main" |
| `REDIS_URL_ANALYTICS` | `redis_analytics` | Redis named "analytics" |
| `MEMCACHED_URL` | `memcached` | Memcached (future) |

Password key convention: `{SERVICE}_PASSWORD` or `{SERVICE}_PASSWORD_{ID}` (e.g. `REDIS_PASSWORD`, `REDIS_PASSWORD_MAIN`).

---

## File Map

**Create:**
- `lib/services/cache_registry.py` — `CacheRegistry`: stores named adapter instances, mirrors `ConnectionRegistry` API
- `lib/services/cache_tester.py` — `CacheTester(SimpleService)`: pings a cache adapter, returns `{alive, latency_ms, info, error}`
- `lib/views/admin/caches.py` — `AdminCachesView`: live status dashboard
- `tests/test_cache_registry.py` — unit tests for registry
- `tests/test_cache_tester.py` — unit tests for tester
- `tests/test_admin_caches_view.py` — view tests

**Modify:**
- `main.py` — scan vault for `*_URL` / `*_URL_*` keys, build adapters, register in `CacheRegistry`, add to props, register `/admin/caches` route
- `tests/test_smoke.py` — add new module imports

---

## Tasks

### Task 1: Build CacheRegistry

**Files:**
- Create: `lib/services/cache_registry.py`
- Create: `tests/test_cache_registry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cache_registry.py`:

```python
import pytest
from lib.services.cache_registry import CacheRegistry
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def clean():
    CacheRegistry._adapters = {}
    yield
    CacheRegistry._adapters = {}

def test_register_and_get():
    adapter = MagicMock()
    CacheRegistry.register("redis", adapter)
    assert CacheRegistry.get("redis") is adapter

def test_get_missing_raises():
    with pytest.raises(RuntimeError, match="not registered"):
        CacheRegistry.get("nonexistent")

def test_list_returns_registered_names():
    CacheRegistry.register("a", MagicMock())
    CacheRegistry.register("b", MagicMock())
    assert set(CacheRegistry.list()) == {"a", "b"}

def test_register_overwrites():
    a, b = MagicMock(), MagicMock()
    CacheRegistry.register("redis", a)
    CacheRegistry.register("redis", b)
    assert CacheRegistry.get("redis") is b
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
python -m pytest tests/test_cache_registry.py -v
```

- [ ] **Step 3: Implement CacheRegistry**

Create `lib/services/cache_registry.py`:

```python
from lib.core.interfaces import SimpleService


class CacheRegistry:
    """Named store for cache adapter instances (Redis, Memcached, etc.)."""
    _adapters: dict[str, SimpleService] = {}

    @classmethod
    def register(cls, name: str, adapter: SimpleService) -> None:
        cls._adapters[name] = adapter

    @classmethod
    def get(cls, name: str) -> SimpleService:
        if name not in cls._adapters:
            raise RuntimeError(f"Cache adapter {name!r} not registered")
        return cls._adapters[name]

    @classmethod
    def list(cls) -> list[str]:
        return list(cls._adapters.keys())
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/test_cache_registry.py -v
```

- [ ] **Step 5: Commit**

```bash
git add lib/services/cache_registry.py tests/test_cache_registry.py
git commit -m "feat: add CacheRegistry for named cache adapter instances"
```

---

### Task 2: Build CacheTester service

**Files:**
- Create: `lib/services/cache_tester.py`
- Create: `tests/test_cache_tester.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cache_tester.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from lib.services.cache_tester import CacheTester
from lib.contracts.base import ActionRequest, ActionResult

@pytest.fixture
def working_adapter():
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(
        success=True, data={"keys": ["key1", "key2"]}
    )
    return adapter

@pytest.fixture
def broken_adapter():
    adapter = MagicMock()
    adapter.execute.side_effect = Exception("Connection refused")
    return adapter

def test_test_returns_alive_true_on_working_adapter(working_adapter):
    tester = CacheTester(working_adapter)
    result = tester.test({})
    assert result["alive"] is True
    assert result["latency_ms"] >= 0
    assert result["error"] is None

def test_test_returns_alive_false_on_broken_adapter(broken_adapter):
    tester = CacheTester(broken_adapter)
    result = tester.test({})
    assert result["alive"] is False
    assert result["latency_ms"] is None
    assert isinstance(result["error"], str)

def test_test_never_raises(broken_adapter):
    tester = CacheTester(broken_adapter)
    result = tester.test({})
    assert isinstance(result, dict)
    assert "alive" in result

def test_test_via_execute_returns_action_result(working_adapter):
    tester = CacheTester(working_adapter)
    result = tester.execute(ActionRequest(action="test", data={}))
    assert isinstance(result, ActionResult)
    assert result.success is True
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
python -m pytest tests/test_cache_tester.py -v
```

- [ ] **Step 3: Implement CacheTester**

Create `lib/services/cache_tester.py`:

```python
import time
from lib.core.interfaces import SimpleService
from lib.contracts.base import ActionRequest


class CacheTester(SimpleService):
    """Ping a cache adapter to check liveness and measure latency.

    Actions:
        test → {alive: bool, latency_ms: float | None, info: str | None, error: str | None}
    """

    def __init__(self, adapter: SimpleService):
        self._adapter = adapter

    def test(self, data: dict) -> dict:
        try:
            start = time.time()
            result = self._adapter.execute(ActionRequest(action="keys", data={"pattern": "*"}))
            latency_ms = (time.time() - start) * 1000

            if result.success:
                count = len(result.data.get("keys", []))
                return {"alive": True, "latency_ms": latency_ms, "info": f"{count} keys", "error": None}
            return {"alive": False, "latency_ms": None, "info": None, "error": result.error}
        except Exception as exc:
            return {"alive": False, "latency_ms": None, "info": None, "error": str(exc)}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/test_cache_tester.py -v
```

- [ ] **Step 5: Commit**

```bash
git add lib/services/cache_tester.py tests/test_cache_tester.py
git commit -m "feat: add CacheTester service for cache adapter liveness checks"
```

---

### Task 3: Build AdminCachesView

**Files:**
- Create: `lib/views/admin/caches.py`
- Create: `tests/test_admin_caches_view.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_admin_caches_view.py`:

```python
import flet as ft
import pytest
from unittest.mock import MagicMock
from lib.views.admin.caches import AdminCachesView
from lib.services.cache_registry import CacheRegistry
from lib.contracts.base import ActionResult
from tests.conftest import FakePage


@pytest.fixture(autouse=True)
def clean_registry():
    CacheRegistry._adapters = {}
    yield
    CacheRegistry._adapters = {}


def make_view(nav_service, redis=None):
    page = FakePage("/admin/caches")
    props = {"nav_service": nav_service, "redis": redis}
    return AdminCachesView(page, props)


def test_view_renders_without_crashing(nav_service):
    rendered = make_view(nav_service).render()
    assert isinstance(rendered, ft.View)


def test_view_shows_empty_state_when_no_caches(nav_service):
    rendered = make_view(nav_service).render()
    view_str = str(rendered.controls)
    assert "No Cache" in view_str or "REDIS_URL" in view_str


def test_view_shows_registered_adapters(nav_service):
    adapter = MagicMock()
    adapter.execute.return_value = ActionResult(success=True, data={"keys": ["k1"]})
    CacheRegistry.register("redis", adapter)

    rendered = make_view(nav_service).render()
    view_str = str(rendered.controls)
    assert "REDIS" in view_str


def test_view_has_correct_title(nav_service):
    assert AdminCachesView.title == "Cache Inspector"


def test_view_shows_sidebar(nav_service):
    assert AdminCachesView.show_sidebar is True
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
python -m pytest tests/test_admin_caches_view.py -v
```

- [ ] **Step 3: Implement AdminCachesView**

Create `lib/views/admin/caches.py`:

```python
"""Admin cache inspector view — Redis, Memcached, and other key-value stores."""
import flet as ft

from lib.services.cache_registry import CacheRegistry
from lib.services.cache_tester import CacheTester
from lib.ui.layouts.base_view import BaseView


def _status_row(label: str, status_text: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Row([
            ft.Text(label, size=14, weight=ft.FontWeight.BOLD, expand=True),
            ft.Text(status_text, size=12, color=color),
        ]),
        padding=15,
        border=ft.border.all(1, "#ddd"),
        border_radius=8,
    )


class AdminCachesView(BaseView):
    """Live status dashboard for all registered cache adapters."""

    title = "Cache Inspector"
    show_sidebar = True

    def _test(self, name: str) -> tuple:
        """Returns (alive, display_info, error) for a named cache."""
        try:
            adapter = CacheRegistry.get(name)
            result = CacheTester(adapter).test({})
            if result["alive"]:
                info = f"🟢 live  {result['latency_ms']:.1f} ms  —  {result['info']}"
                return True, info, None
            return False, f"🔴 down  {result['error']}", result["error"]
        except Exception as exc:
            return False, f"🔴 error  {exc}", str(exc)

    def build_content(self):
        names = CacheRegistry.list()

        if not names:
            return ft.Column([
                ft.Text("No Cache Services Configured", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Vault conventions:", size=14, color="grey"),
                ft.Text("  REDIS_URL              → single Redis instance",  size=12, color="grey", italic=True),
                ft.Text("  REDIS_URL_MAIN         → Redis named 'main'",     size=12, color="grey", italic=True),
                ft.Text("  REDIS_PASSWORD         → shared Redis password",   size=12, color="grey", italic=True),
                ft.Text("  REDIS_PASSWORD_MAIN    → password for 'main'",    size=12, color="grey", italic=True),
            ], spacing=8)

        rows = []
        for name in sorted(names):
            alive, display, _ = self._test(name)
            rows.append(_status_row(name.upper(), display, "green" if alive else "red"))

        return ft.Column([
            ft.Text("Cache Services", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            *rows,
        ], spacing=15)


def view(page: ft.Page, props: dict) -> ft.View:
    """Router entry point."""
    return AdminCachesView(page, props).render()
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/test_admin_caches_view.py -v
```

- [ ] **Step 5: Commit**

```bash
git add lib/views/admin/caches.py tests/test_admin_caches_view.py
git commit -m "feat: add AdminCachesView at /admin/caches"
```

---

### Task 4: Wire CacheRegistry into main.py

**Files:**
- Modify: `main.py`

**Convention scanner logic** — vault keys matching `{SERVICE}_URL` or `{SERVICE}_URL_{ID}`:

| Vault key | Parsed service | Parsed ID | Registry name |
|---|---|---|---|
| `REDIS_URL` | `redis` | *(none)* | `redis` |
| `REDIS_URL_MAIN` | `redis` | `main` | `redis_main` |
| `REDIS_URL_ANALYTICS` | `redis` | `analytics` | `redis_analytics` |

Password is looked up by `{SERVICE}_PASSWORD` or `{SERVICE}_PASSWORD_{ID}`.

- [ ] **Step 1: Write failing test (import check)**

In `tests/test_smoke.py`, add to the parametrize list:
```python
"lib.services.cache_registry",
"lib.services.cache_tester",
"lib.views.admin.caches",
```

Run:
```bash
python -m pytest tests/test_smoke.py -v
```
Expected: PASS (modules already exist from previous tasks).

- [ ] **Step 2: Add scanner to main.py**

After `vault.unlock()` and the `DATABASE_*` loop, add:

```python
from lib.services.cache_registry import CacheRegistry

# Scan vault for SERVICE_URL and SERVICE_URL_ID keys to auto-register cache adapters.
# Supported services: REDIS (uses RedisAdapter), extensible for MEMCACHED etc.
_CACHE_BUILDERS = {
    "REDIS": lambda host, port, password: RedisAdapter(host=host, port=port or 6379, password=password or ""),
}

for key in vault.keys():
    parts = key.split("_URL", 1)       # e.g. "REDIS_URL_MAIN" → ["REDIS", "_MAIN"]
    if len(parts) != 2:
        continue
    service = parts[0]                  # "REDIS"
    id_suffix = parts[1].lstrip("_").lower()  # "main" or "" for bare _URL
    builder = _CACHE_BUILDERS.get(service)
    if builder is None:
        continue

    registry_name = f"{service.lower()}_{id_suffix}" if id_suffix else service.lower()
    password_key = f"{service}_PASSWORD_{id_suffix.upper()}" if id_suffix else f"{service}_PASSWORD"

    try:
        from urllib.parse import urlparse
        parsed = urlparse(vault.get(key))
        password = vault.get(password_key, "")
        adapter = builder(parsed.hostname, parsed.port, password)
        CacheRegistry.register(registry_name, adapter)
    except Exception as e:
        print(f"Warning: Failed to register cache '{registry_name}': {e}")
```

- [ ] **Step 3: Register /admin/caches route**

In the router setup section, add:
```python
router.register("/admin/caches", "lib.views.admin.caches")
```

- [ ] **Step 4: Run full test suite**

```bash
python -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_smoke.py
git commit -m "feat: wire CacheRegistry into main.py with SERVICE_URL_ID vault convention"
```

---

## Success Criteria

- [ ] `CacheRegistry` stores named adapters, same API shape as `ConnectionRegistry`
- [ ] `CacheTester` pings any cache adapter, never raises, returns `{alive, latency_ms, info, error}`
- [ ] `/admin/caches` renders live status for all registered cache instances
- [ ] Vault convention `REDIS_URL` / `REDIS_URL_ID` + `REDIS_PASSWORD` / `REDIS_PASSWORD_ID` auto-registers without code changes
- [ ] All existing tests still pass
- [ ] New modules appear in smoke tests

## Adding a New Cache Instance (Zero Code Changes)

```
In /security vault:
  REDIS_URL_SESSIONS  = redis://192.168.0.108:6380
  REDIS_PASSWORD_SESSIONS = s3cr3t

Restart app → /admin/caches shows REDIS_SESSIONS 🟢 live
```
