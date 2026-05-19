---
title: "Recipes: Adding Services, Views, Routes, Models"
category: guide
audience: [developer, agent]
related:
  - ../core/CONVENTIONS.md
  - API_DEVELOPMENT.md
  - VIEW_DEVELOPMENT.md
agent_priority: medium
---

# Adding Stuff — The Easy Guide

This is the cheat sheet for everyday tasks. No theory, just copy/paste recipes.

---

## 1. Add a new page

The router is **convention-based**: filename = URL.

| File | URL |
|---|---|
| `lib/views/dashboard.py` | `/dashboard` |
| `lib/views/admin/users.py` | `/admin/users` |
| `lib/views/profile.py` | `/profile` |

**Step 1.** Create the file. Subclass `BaseView` and expose a `view()` function:

```python
# lib/views/dashboard.py
import flet as ft
from lib.ui.layouts.base_view import BaseView


class DashboardView(BaseView):
    title = "Dashboard"

    def build_content(self):
        return ft.Column([
            ft.Text("My Dashboard", size=28, weight=ft.FontWeight.BOLD),
            ft.Text("Hello world"),
        ])


def view(page: ft.Page, props: dict) -> ft.View:
    return DashboardView(page, props).render()
```

**Step 2.** Add it to the sidebar (optional). Edit [lib/ui/layouts/base_view.py](../lib/ui/layouts/base_view.py):

```python
SIDEBAR_ITEMS = [
    ("Home", "/"),
    ("Login", "/login"),
    ("Products", "/products"),
    ("Dashboard", "/dashboard"),  # ← add here
]
```

**Step 3.** Restart the app. Visit `/dashboard`. Done.

---

## 2. Hide or swap parts of the layout

`BaseView` has three boolean toggles. Set them on the class:

```python
class LoginView(BaseView):
    title = "Login"
    show_sidebar = False     # no left bar
    show_appbar = True       # default
    show_bottombar = False   # default

    def build_content(self):
        return ...
```

To **swap** a piece for a custom one, override its `build_*` method:

```python
class FancyView(BaseView):
    def build_appbar(self):
        return ft.AppBar(title=ft.Text("Custom!"), bgcolor=ft.Colors.RED_700)

    def build_sidebar(self):
        return ft.Container(content=ft.Text("My weird sidebar"), width=180)

    def build_content(self):
        return ...
```

The available pieces:

| Method | What it returns | Toggle |
| --- | --- | --- |
| `build_appbar()` | `ft.AppBar` | `show_appbar` |
| `build_sidebar()` | any `ft.Control` | `show_sidebar` |
| `build_bottombar()` | `ft.AppBar` | `show_bottombar` |
| `build_content()` | any `ft.Control` (or list/string) | required |

---

## 3. Add a parameterized route (`/products/{id}`)

**Step 1.** Define a Pydantic model for the params on your view class:

```python
# lib/views/product_detail.py
from pydantic import BaseModel
from lib.ui.layouts.base_view import BaseView


class ProductDetailView(BaseView):
    title = "Product"

    class Params(BaseModel):
        id: int                       # from URL path /products/{id}
        tab: str = "overview"         # from query string ?tab=stock

    def build_content(self):
        p = self.params               # already typed and validated
        return ft.Text(f"Product #{p.id}, tab={p.tab}")


def view(page, props):
    return ProductDetailView(page, props).render()
```

**Step 2.** Register the route in [main.py](../main.py):

```python
router.register("/products/{id}", "lib.views.product_detail")
```

That's it. Now:

- `/products/42` → `params.id = 42`, `params.tab = "overview"`
- `/products/42?tab=stock` → `params.id = 42`, `params.tab = "stock"`
- `/products/abc` → Pydantic raises a clear validation error (id isn't an int)

**Where do params come from?**

| Source | Lives in `props` as | Example |
| --- | --- | --- |
| URL path (`/products/{id}`) | `props["params"]` | `{"id": "42"}` |
| Query string (`?tab=stock`) | `props["query"]` | `{"tab": "stock"}` |

If you don't define a `Params` class, just read those dicts directly:

```python
def build_content(self):
    pid = self.props["params"].get("id")
    tab = self.props["query"].get("tab", "overview")
```

---

## 4. Add a navigation button

```python
from lib.ui.components.nav_button import NavButton

NavButton("Go to Profile", "/profile", self.nav_service)
```

For a parameterized URL, just include the value:

```python
NavButton("View Order #42", "/orders/42?ref=email", self.nav_service)
```

---

## 5. Add a back button

```python
from lib.ui.components.back_button import BackButton

BackButton(self.nav_service)
```

(The top app bar already shows a back arrow when there's history. Use this for putting one in the page body.)

---

## 6. Add a button that does an action (NOT navigation)

Just plain Flet:

```python
import flet as ft

ft.ElevatedButton("Click Me", on_click=lambda _: print("hi!"))
```

For more (e.g. show a snackbar):

```python
def show_message(_):
    self.page.snack_bar = ft.SnackBar(ft.Text("Saved!"))
    self.page.snack_bar.open = True
    self.page.update()

ft.ElevatedButton("Save", on_click=show_message)
```

---

## 7. Fire a service action

When you want to call into business logic, wrap it in an `ActionRequest`:

```python
from lib.contracts.base import ActionRequest

def create_user(_):
    user_service = self.props["user_service"]   # injected via props
    result = user_service.execute(ActionRequest(
        action="create_user",
        data={"username": "alice"},
    ))
    if result.success:
        print("Created:", result.data)
    else:
        print("Error:", result.error)

ft.ElevatedButton("Create User", on_click=create_user)
```

Why bother? Because *every* service speaks the same language — you can swap a fake test service in and your UI doesn't change.

---

## 8. Listen for an event

```python
def on_route_change(event):
    print("New URL:", event.payload["url"])

event_bus.subscribe("nav.route_changed", on_route_change)
```

Common events the system already fires:

- `nav.route_changed` — payload: `{url, can_go_back, can_go_forward}`

Publish your own from any service:

```python
from lib.contracts.base import Event

event_bus.publish(Event(type="user.created", payload={"id": 42}))
```

---

## 9. Pass a service into every view

Edit [main.py](../main.py) where `set_props_factory` is set:

```python
router.set_props_factory(lambda: {
    "nav_service": nav_service,
    "user_service": user_service,    # ← add here
    "event_bus": event_bus,
})
```

Now every view has `self.props["user_service"]` available.

---

## 10. Make a custom component

Drop a class in `lib/ui/components/`. It's just a Flet control with the constructor hardcoded:

```python
# lib/ui/components/badge.py
import flet as ft


class Badge(ft.Container):
    def __init__(self, text: str, color=ft.Colors.BLUE_400):
        super().__init__(
            content=ft.Text(text, size=12, color=ft.Colors.WHITE),
            bgcolor=color,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=12,
        )
```

Use it:

```python
from lib.ui.components.badge import Badge

Badge("NEW", color=ft.Colors.GREEN_400)
```

---

## 11. Connect a SQL database

All connections are registered at startup from vault secrets — no code changes needed for new instances.

### The default (app) database

Set `POSTGRES_URL` in the vault. This becomes `"postgres"` in `ConnectionRegistry` and is what `UserRepository` uses. It also appears as **POSTGRES** in `/admin/databases`.

```
Vault key: POSTGRES_URL
Value:      postgresql://user:pass@host:5432/mydb
Registry:   ConnectionRegistry.get("postgres")
```

### Additional named databases (for inspection / reporting)

Add a `DATABASE_<NAME>` key in the vault. Each one is registered automatically under that name.

```
Vault key: DATABASE_ANALYTICS
Value:      postgresql://user:pass@host:5432/analytics
Registry:   ConnectionRegistry.get("analytics")

Vault key: DATABASE_LEGACY
Value:      mysql+pymysql://user:pass@host/legacydb
Registry:   ConnectionRegistry.get("legacy")
```

These show up in `/admin/databases` next to POSTGRES. Add as many as you want — just restart the app.

### Use a database in a view or service

```python
from lib.database.session import ConnectionRegistry
from lib.database.query import safe_query

def build_content(self):
    factory = ConnectionRegistry.get("analytics")   # or "postgres"
    with factory.session() as session:
        rows = safe_query(session, "SELECT * FROM orders WHERE status = :s", s="open")
    return ft.Text(f"{len(rows)} open orders")
```

For ORM-based access, use a repository:

```python
from lib.repositories.user_repository import UserRepository
from lib.database.session import ConnectionRegistry

user_repo = UserRepository(ConnectionRegistry.get("postgres"))
users = user_repo.list()
```

---

## 12. Connect a cache (Redis, etc.)

Cache adapters follow a `SERVICE_URL[_ID]` convention in the vault.

### Single Redis instance

```
Vault key: REDIS_URL
Value:      redis://192.168.0.100:6379
Password:   REDIS_PASSWORD   (optional)
Registry:   CacheRegistry.get("redis")
```

### Multiple Redis instances

```
Vault key: REDIS_URL_MAIN        → CacheRegistry.get("redis_main")
Vault key: REDIS_URL_SESSIONS    → CacheRegistry.get("redis_sessions")
Passwords: REDIS_PASSWORD_MAIN, REDIS_PASSWORD_SESSIONS
```

All registered instances appear in `/admin/caches` automatically.

### Use a cache adapter in a view or service

```python
from lib.services.cache_registry import CacheRegistry
from lib.contracts.base import ActionRequest

def save_to_cache(_):
    redis = CacheRegistry.get("redis")
    result = redis.execute(ActionRequest(action="set", data={
        "key": "session:abc123",
        "value": "user_id:42",
        "ttl": 3600,           # seconds (optional)
    }))
    if result.success:
        print("Stored!")

def read_from_cache(_):
    redis = CacheRegistry.get("redis")
    result = redis.execute(ActionRequest(action="get", data={"key": "session:abc123"}))
    if result.success and result.data["found"]:
        print(result.data["value"])
```

Available actions on `RedisAdapter`: `get`, `set`, `delete`, `exists`, `keys`, `expire`, `ttl`.

### Add a new cache type (not Redis)

Add one entry to `_CACHE_BUILDERS` in [main.py](../main.py):

```python
_CACHE_BUILDERS = {
    "REDIS":     lambda host, port, password: RedisAdapter(host=host, port=port or 6379, password=password or ""),
    "MEMCACHED": lambda host, port, password: MemcachedAdapter(host=host, port=port or 11211),
}
```

Then set `MEMCACHED_URL` in the vault — it auto-registers as `"memcached"`.

---

## File map

```
lib/
├── contracts/base.py              ← ActionRequest, ActionResult, Event
├── core/events.py                 ← EventBus
├── services/                      ← Business logic
├── ui/
│   ├── components/                ← Buttons, cards, sidebars (LEGO bricks)
│   └── layouts/base_view.py       ← BaseView — page template
└── views/                         ← One file per page
main.py                            ← Wires everything + registers routes
```

Most days you'll only touch `lib/views/` and `lib/ui/components/`.
