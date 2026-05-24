---
title: "View Development Guide (Flet)"
category: guide
audience: [developer, agent]
related:
  - WRAPPERS.md
  - ../core/CONTRACTS_GUIDE.md
  - ../troubleshooting/ANTI_PATTERNS.md
agent_priority: medium
---

# View Development Guide

How to build Flet UI views in FlexTemplates — the props pattern, calling services,
handling events safely, async patterns, and the common UI shapes you'll reuse.

**Prerequisites:** Read [GETTING_STARTED.md](GETTING_STARTED.md) and
[CONVENTIONS.md](../core/CONVENTIONS.md). Every view subclasses `BaseView`, receives
services through a `props` dict, and calls them via `service.execute(ActionRequest(...))`.
If you understand that, the rest is just Flet mechanics.

**Related docs:**
- [CONVENTIONS.md](../core/CONVENTIONS.md) — naming rules, import rules, module layout
- [GETTING_STARTED.md](GETTING_STARTED.md) — end-to-end walkthrough
- [ANTI_PATTERNS.md](../troubleshooting/ANTI_PATTERNS.md) — view anti-patterns and how to avoid them
- [CONTRACTS_GUIDE.md](../core/CONTRACTS_GUIDE.md) — `ActionRequest` / `ActionResult`

---

## Table of Contents

1. [Quick Example](#quick-example)
2. [The Props Pattern](#the-props-pattern)
3. [Calling Services from Views](#calling-services-from-views)
4. [Event Handlers](#event-handlers)
5. [Common Patterns](#common-patterns)
6. [Reference: View File Structure](#reference-view-file-structure)

---

## Quick Example

A complete view that calls a service and displays results with error handling.
This is the canonical shape every view in the codebase follows.

```python
# lib/views/users.py
import flet as ft

from lib.contracts.base import ActionRequest
from lib.ui.layouts.base_view import BaseView


class UsersView(BaseView):
    title = "Users"
    show_sidebar = True

    def build_content(self):
        user_service = self.props["user_service"]

        # 1. Call the service
        # Old way (still works):
        result = user_service.execute(ActionRequest(action="list"))
        # New way (easier): result = user_service.list_users()  # Wrapper method

        # 2. Handle failure
        if not result.success:
            return ft.Text(f"Failed to load users: {result.error}",
                           color=ft.Colors.RED_400)

        users = result.data.get("users", [])

        # 3. Handle empty state
        if not users:
            return ft.Text("No users yet.", color=ft.Colors.BLUE_GREY_300)

        # 4. Render the data
        return ft.Column(
            [
                ft.Text("Users", size=24, weight=ft.FontWeight.BOLD),
                *[ft.Text(f"{u['username']} ({u['email']})") for u in users],
            ],
            spacing=10,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    """Router entry point — every view module exports this function."""
    return UsersView(page, props).render()
```

Three things every view does:

1. **Subclass `BaseView`** — gives you `self.page`, `self.props`, `self.nav_service`, and the `render()` wiring.
2. **Implement `build_content()`** — returns one `ft.Control` (usually a `Column`).
3. **Export `view(page, props)`** — the router calls this. Always `return SomeView(page, props).render()`.

The four steps inside `build_content` — call, check `success`, handle empty, render — show up in 90% of views. Internalize that shape before reaching for anything fancier.

See [`lib/views/home.py`](../lib/views/home.py), [`lib/views/products.py`](../lib/views/products.py), and [`lib/views/admin/databases.py`](../lib/views/admin/databases.py) for live examples in the codebase.

---

## The Props Pattern

Views never import services directly. They receive everything through a `props`
dict that the router injects on every navigation. This is the project's form of
dependency injection — and it's the single rule that keeps the UI layer swappable.

### 2.1 Receiving Props

Every view module ends with a top-level `view(page, props)` function. The
`BaseView` constructor takes those two arguments and stores them:

```python
class MyView(BaseView):
    def build_content(self):
        # props is available as self.props
        user_service = self.props["user_service"]
        nav_service  = self.nav_service   # shortcut — same as self.props["nav_service"]
        page         = self.page          # the Flet page object
        ...


def view(page: ft.Page, props: dict) -> ft.View:
    return MyView(page, props).render()
```

`BaseView.__init__` enforces that `props["nav_service"]` is present and raises
a clear `KeyError` if it isn't. Everything else is optional — your view decides
what it needs.

For services your view always uses, cache them in `__init__` rather than
re-fetching every render:

```python
class SecurityView(BaseView):
    def __init__(self, page, props):
        super().__init__(page, props)      # always call this first
        self._vault_service = props["vault_service"]
```

That's the pattern in [`lib/views/security.py`](../lib/views/security.py).

### 2.2 What's Available in Props

The router builds `props` from `set_props_factory()` in [`main.py`](../main.py).
The current factory provides:

| Key | Type | Purpose |
|---|---|---|
| `nav` | `Nav` | Simple navigation API: `self.nav.go("/login")` |
| `vault` | `Vault` | Simple secrets API: `self.vault.get("KEY")` |
| `events` | `Events` | Simple event bus: `self.events.emit(...)` |
| `nav_service` | `NavigationService` | Full service — used by framework internals |
| `vault_service` | `VaultService` | Full service — `.execute(ActionRequest(...))` |
| `user_repo` | `UserRepository` | Direct data access |
| `redis` | `RedisAdapter` | Default cache adapter, if registered |
| `config` | `AppConfig` | App configuration |
| `connection_tester` | `ConnectionTester` | DB liveness probe |
| `cache_tester` | `CacheTester` | Cache liveness probe |
| `params` | `dict` | URL path params (e.g. `{"id": "42"}` from `/users/{id}`) |
| `query` | `dict` | Parsed query string (e.g. `{"tab": "stock"}` from `?tab=stock`) |
| `product_service` | `ProductService` | Product CRUD — list, get, create, update, delete |
| `backend` | `IBackendAdapter` | Auth + user/role/job CRUD for admin views |
| `dev_nav` | `bool` | Show the orange floating dev nav |

**Note:** The table above shows `main.py`'s default props. The rest of this guide assumes you've added `user_service` and `role_service` to the props factory as shown in section 2.2.

Add a new key when you wire a new service — edit the lambda in `main.py`:

```python
router.set_props_factory(lambda: {
    ...
    "user_service": user_service,    # add this line
    "order_service": order_service,  # and this one
})
```

The router calls the factory fresh on every navigation, so swapping
implementations at runtime works without restarts.

### 2.3 Injection vs Hardcoding

The single biggest mistake in view code is reaching for an import when you
should reach for `self.props`. Compare:

```python
# WRONG — views must never import services directly
from lib.services.user_service import UserService

class UsersView(BaseView):
    def build_content(self):
        service = UserService(SessionFactory(...))   # builds its own deps
        result = service.execute(ActionRequest(action="list"))
        ...
```

```python
# CORRECT — services arrive via props
class UsersView(BaseView):
    def build_content(self):
        service = self.props["user_service"]
        result = service.execute(ActionRequest(action="list"))
        ...
```

Why the rule matters:

- **Tests can swap services.** A test rendering the view passes a mock service in `props`. Hardcoded imports leave no seam.
- **No circular imports.** Views depend on `props`. Services don't reach back into UI.
- **Container is the single wiring point.** Want to change `UserService` to a remote API client? Change `main.py`. The views don't move.

**Exception — registries.** `ConnectionRegistry` and `CacheRegistry` are
class-level singletons (no instance state). Views may import them directly to
enumerate names, as `admin/databases.py` does:

```python
# OK — registries are global lookup tables, not stateful services
from lib.database.session import ConnectionRegistry

names = ConnectionRegistry.list()
```

For everything else: if it has a constructor, it goes through props.

### 2.4 Protected Views (Auth Guard)

Views that require login subclass `ProtectedView` instead of `BaseView`. The
redirect to `/login` is automatic — no manual check needed in `build_content`:

```python
from lib.ui.layouts.protected_view import ProtectedView

class ManageUsersView(ProtectedView):    # auth check is automatic
    title = "Manage Users"
    show_sidebar = True

    def build_content(self):
        backend = self.props["backend"]
        result = backend.list_users(page=1, page_size=20)
        ...
```

`ProtectedView.render()` checks `backend.current_user()` before calling
`super().render()`. If `current_user()` returns `None`, it redirects to `/login`
and returns an empty view.

**When to subclass `ProtectedView`:**
- Any admin or management view (user management, roles, scheduler, security)
- Any view that accesses data that should not be public

**When to stay on `BaseView`:**
- `/login` itself — it IS the auth entry point
- Public pages: `/`, `/products`, `/not_found`

**Current protected views:** `SecurityView`, `ManageUsersView`, `ManageRolesView`,
`AdminSchedulerView`, `AdminDatabasesView`, `AdminCachesView`.

---

## Calling Services from Views

Services speak one language: `service.execute(ActionRequest(...))` returns an
`ActionResult`. Views handle both halves of that contract.

### 3.1 The Standard Call

```python
from pydantic import BaseModel
from lib.contracts.base import ActionRequest

class UserDetailView(BaseView):
    class Params(BaseModel):
        id: str

    def build_content(self):
        user_service = self.props["user_service"]

        result = user_service.execute(
            ActionRequest(action="get", data={"id": self.params.id})
        )

        if not result.success:
            return ft.Text(result.error, color=ft.Colors.RED_400)

        user = result.data
        return ft.Column([
            ft.Text(user["username"], size=24, weight=ft.FontWeight.BOLD),
            ft.Text(user["email"]),
        ])
```

The shape is always the same:

1. Build an `ActionRequest(action=..., data={...})`.
2. Call `service.execute(request)`.
3. Check `result.success`.
4. Read `result.data` on success, `result.error` on failure.

`ActionResult` is defined in [`lib/contracts/base.py`](../lib/contracts/base.py):

```python
class ActionResult(BaseModel):
    success: bool
    data: dict[str, Any] = {}
    events: list[Event] = []
    error: str | None = None
```

### 3.2 Wrapper Methods (the Easier Way)

Services often expose convenience wrapper methods that skip the `ActionRequest`
boilerplate. `UserService` and `RoleService` both do this. Prefer them when
they exist:

```python
# Long form — works everywhere
result = user_service.execute(ActionRequest(action="get", data={"id": user_id}))
user = result.data if result.success else None

# Short form — equivalent, easier to read
user = user_service.get_user(user_id)   # returns dict (empty on miss/error)
```

**Available wrapper methods:** See [WRAPPERS.md](WRAPPERS.md) for the full list (`list_users`, `get_user`, `create_user`, `delete_user`, `stage_user_with_roles`, etc.)

When to use which:

- **Wrappers** — for one-shot reads where you trust the service to raise on bad input. Cleaner in view code.
- **`execute(ActionRequest)`** — for actions you build dynamically, when you need `result.events`, or when you want the full `success`/`error` envelope without try/except.

See [GETTING_STARTED.md → Step 4](GETTING_STARTED.md#step-4-use-the-wrapper-methods-5-minutes)
for the wrapper-method cheat sheet on `UserService` and `RoleService`.

The `Nav` and `Vault` helpers in props are pure wrapper objects:

```python
# Instead of:
self.nav_service.execute(ActionRequest(action="visit", data={"url": "/login"}))

# Use:
self.nav.go("/login")

# Instead of:
result = self.vault_service.execute(ActionRequest(action="get", data={"key": "DATABASE_POSTGRES"}))
url = result.data["value"] if result.success else None

# Use:
url = self.vault.get("DATABASE_POSTGRES")
```

### 3.3 Handling `ActionResult`

Three things to check on every result:

```python
result = user_service.execute(ActionRequest(action="create", data=form_data))

# 1. success — always the first branch
if not result.success:
    self._error_text.value = result.error
    self.page.update()
    return

# 2. data — the payload, shape depends on the action
new_user = result.data        # e.g. {"id": "...", "username": "..."}

# 3. events — domain events the service emitted (often empty)
for event in result.events:
    if event.type == "user.created":
        self._show_snackbar(f"Welcome, {event.payload['username']}!")
```

Most views don't touch `result.events`. They become useful once you wire the
`EventBus` into UI side effects (toast notifications, audit logs). For a
read-heavy view, `success` + `data` is all you need.

### 3.4 Displaying Errors

Two patterns cover everything:

**Inline error text** — for forms and validation:

```python
class CreateUserView(BaseView):
    def __init__(self, page, props):
        super().__init__(page, props)
        self._error_text = ft.Text("", color=ft.Colors.RED_400, size=12)

    def _on_submit(self, e):
        result = self.props["user_service"].execute(
            ActionRequest(action="create", data={
                "username": self._username.value,
                "email": self._email.value,
            })
        )
        if result.success:
            self.nav.go("/users")
        else:
            self._error_text.value = result.error or "Create failed"
            self.page.update()
```

**Snackbar toast** — for transient feedback after a successful action:

```python
def _show_snackbar(self, message: str, duration: int = 1500):
    snack = ft.SnackBar(content=ft.Text(message), duration=duration)
    self.page.overlay.append(snack)
    snack.open = True
    self.page.update()


def _on_delete(self, user_id):
    result = self.props["user_service"].execute(
        ActionRequest(action="delete", data={"id": user_id})
    )
    if result.success:
        self._show_snackbar(f"User deleted")
        self._refresh_list()
    else:
        self._show_snackbar(f"Failed: {result.error}", duration=3000)
```

Helper lives on `BaseView` subclasses or any view — see
[`lib/views/security.py`](../lib/views/security.py) `_show_snackbar` for the
working version.

---

## Event Handlers

Flet calls your handler with a single event argument when a button is clicked,
a field changes, or a route fires. Handlers run on the Flet event loop — they
must not crash silently and must explicitly call `page.update()` when they
mutate UI state.

### 4.1 The Safe Handler Pattern

Wrap every handler in try/except. An uncaught exception inside Flet's loop
disappears into the console without a traceback in the UI:

```python
class CreateUserView(BaseView):
    def __init__(self, page, props):
        super().__init__(page, props)
        self._username = ft.TextField(label="Username")
        self._email    = ft.TextField(label="Email")
        self._error    = ft.Text("", color=ft.Colors.RED_400, size=12)

    def _on_submit(self, e):
        try:
            result = self.props["user_service"].execute(
                ActionRequest(action="create", data={
                    "username": self._username.value.strip(),
                    "email":    self._email.value.strip(),
                })
            )
            if result.success:
                self._error.value = ""
                self.nav.go("/users")
            else:
                self._error.value = result.error or "Create failed"
                self.page.update()
        except Exception as exc:
            self._error.value = f"Unexpected error: {exc}"
            self.page.update()

    def build_content(self):
        return ft.Column([
            ft.Text("New User", size=24, weight=ft.FontWeight.BOLD),
            self._username,
            self._email,
            self._error,
            ft.ElevatedButton("Create", on_click=self._on_submit),
        ], spacing=15)
```

Rules of thumb:

- Validate inputs **before** the service call. Empty strings, bad emails, etc.
- Set error text on failure, call `page.update()`, and `return` early.
- Navigate (`self.nav.go(...)`) on success — the route change triggers a fresh render.

### 4.2 Calling Services in Event Handlers

The same pattern as `build_content`, but the handler is responsible for
refreshing the UI afterwards (Flet doesn't auto-rebuild views):

```python
def _on_delete_user(self, user_id):
    """Delete handler — bound via lambda in the row builder."""
    result = self.props["user_service"].execute(
        ActionRequest(action="delete", data={"id": user_id})
    )
    if result.success:
        # Mutate local state, then redraw the affected control
        self._users = [u for u in self._users if u["id"] != user_id]
        self._refresh_list()
    else:
        self._error.value = result.error
        self.page.update()
```

**Beware the lambda closure trap.** This binds `user_id` correctly because
each iteration captures it as a default-argument value:

```python
# CORRECT — uid is captured at definition time
for u in users:
    rows.append(
        ft.IconButton(
            ft.Icons.DELETE,
            on_click=lambda e, uid=u["id"]: self._on_delete_user(uid),
        )
    )
```

This does NOT work — every button ends up deleting the last user, because the
`u` name is rebound on each loop:

```python
# WRONG — late-binding closure
for u in users:
    rows.append(
        ft.IconButton(
            ft.Icons.DELETE,
            on_click=lambda e: self._on_delete_user(u["id"]),  # u is the LAST iteration
        )
    )
```

### 4.3 Async in Flet

Flet handlers are synchronous by default, but the page exposes an event loop
for long work. Two cases come up:

**Quick service call** — just call it. Service execute is sync, returns
immediately:

```python
def _on_refresh(self, e):
    result = self.props["user_service"].execute(ActionRequest(action="list"))
    if not result.success:
        self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {result.error}"))
        self.page.snack_bar.open = True
        self.page.update()
        return
    self._users = result.data.get("users", [])
    self._refresh_list()
```

**Slow work (network, DB probe, file I/O)** — schedule it on the Flet event loop
so the UI stays responsive. The pattern in `admin/databases.py`:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

def build_content(self):
    body = ft.Column(spacing=10)
    names = ["Postgres", "Redis", "MongoDB"]   # or: [c for c in CacheRegistry.list()]

    async def _run_probe():
        # Run blocking work in a thread pool so we don't freeze the UI
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as ex:
            results = await loop.run_in_executor(
                None, lambda: list(ex.map(self._probe, names))
            )
        # Back on the event loop — safe to mutate UI and call page.update()
        type(self)._status_cache.update(dict(zip(names, results)))
        self._fill_body(body)
        self.page.update()

    self._fill_body(body)              # immediate render with placeholders
    self.page.run_task(_run_probe)     # kick off async refresh
    return body
```

Key calls:

- `self.page.run_task(coro)` — schedule an `async def` on the Flet loop. Use this from any handler when you want async work.
- `loop.run_in_executor(None, blocking_fn)` — push a blocking call into a thread pool.
- `self.page.update()` — call this once you mutate UI state. It pushes the deltas to the client.

### 4.4 Page Updates

Three update calls. Use the smallest that covers your change:

| Call | Use when |
|---|---|
| `self.page.update()` | You changed multiple controls anywhere on the page. Safe default. |
| `control.update()` | You changed exactly one control. Cheaper if you have the reference. |
| `self.page.go(url)` | You want to navigate — triggers a full route change and re-render. |

Common mistake: forgetting `page.update()` after mutating a state variable.
The view doesn't auto-refresh:

```python
def _on_toggle_reveal(self, key):
    self._reveal_key = key if self._reveal_key != key else None
    self.page.update()   # without this, nothing visibly changes
```

If you swap a control's `content`, you can update just the container:

```python
self._content_container.content = self._build_unlocked()
self._content_container.update()
```

That's how [`security.py`](../lib/views/security.py) swaps between locked /
unlocked / show-keys states without rebuilding the whole view.

---

## Common Patterns

The four UI shapes that cover most views.

> **Helper used throughout this section** — several examples call
> `self._refresh_list()` to rebuild a `ft.Column` of user rows from the cached
> `self._users` list. Define it once on your view class:
>
> ```python
> def _refresh_list(self):
>     """Rebuild the users list control from self._users."""
>     self.body.controls.clear()
>     for u in self._users:
>         self.body.controls.append(
>             ft.ListTile(
>                 title=ft.Text(u["username"]),
>                 on_click=lambda e, uid=u["id"]: self._view_user(uid),
>             )
>         )
>     self.page.update()
> ```
>
> The examples below assume `self.body` is the `ft.Column` returned from
> `build_content()` and `self._users` is the cached list of user dicts.

### 5.1 Forms

Capture user input, validate, call a service, render success/error:

```python
class CreateRoleView(BaseView):
    title = "New Role"

    def __init__(self, page, props):
        super().__init__(page, props)
        self._name        = ft.TextField(label="Name", width=320)
        self._description = ft.TextField(label="Description", multiline=True, width=320)
        self._error       = ft.Text("", color=ft.Colors.RED_400, size=12)

    def _on_submit(self, e):
        name = self._name.value.strip()
        if not name:
            self._error.value = "Name is required"
            self.page.update()
            return

        result = self.props["role_service"].execute(
            ActionRequest(action="create", data={
                "name": name,
                "description": self._description.value.strip(),
            })
        )
        if result.success:
            self.nav.go("/roles")
        else:
            self._error.value = result.error or "Failed to create role"
            self.page.update()

    def build_content(self):
        return ft.Column([
            ft.Text("New Role", size=24, weight=ft.FontWeight.BOLD),
            self._name,
            self._description,
            self._error,
            ft.Row([
                ft.ElevatedButton("Create", on_click=self._on_submit),
                ft.TextButton("Cancel", on_click=lambda e: self.nav.go("/roles")),
            ], spacing=10),
        ], spacing=15)


def view(page, props):
    return CreateRoleView(page, props).render()
```

Form discipline:

- Keep field references on `self` so handlers can read them.
- Validate before calling the service.
- One `_error` Text control — easier than scattering errors per field.
- On success, navigate away. The next view re-renders from scratch.

### 5.2 Lists and Tables

The empty / loading / loaded states are the trick. Always render all three:

```python
class UsersListView(BaseView):
    title = "Users"

    def build_content(self):
        result = self.props["user_service"].execute(ActionRequest(action="list"))

        if not result.success:
            return ft.Text(f"Error: {result.error}", color=ft.Colors.RED_400)

        users = result.data.get("users", [])

        if not users:
            return ft.Column([
                ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=42,
                        color=ft.Colors.BLUE_GREY_400),
                ft.Text("No users yet", size=18),
                ft.ElevatedButton("Create User",
                                  on_click=lambda e: self.nav.go("/users/new")),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

        rows = [
            ft.DataRow([
                ft.DataCell(ft.Text(u["username"])),
                ft.DataCell(ft.Text(u["email"])),
                ft.DataCell(
                    ft.IconButton(
                        ft.Icons.DELETE,
                        on_click=lambda e, uid=u["id"]: self._on_delete(uid),
                    )
                ),
            ])
            for u in users
        ]

        return ft.Column([
            ft.Text(f"Users ({len(users)})", size=24, weight=ft.FontWeight.BOLD),
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Username")),
                    ft.DataColumn(ft.Text("Email")),
                    ft.DataColumn(ft.Text("Actions")),
                ],
                rows=rows,
            ),
        ], spacing=15)

    def _on_delete(self, user_id):
        result = self.props["user_service"].execute(
            ActionRequest(action="delete", data={"id": user_id})
        )
        if not result.success:
            self._error.value = result.error
            self.page.update()
            return

        # Refresh the users list from the database (page.go(page.route) is a
        # no-op in Flet, so we re-fetch and rebuild explicitly).
        list_result = self.props["user_service"].execute(
            ActionRequest(action="list")
        )
        if list_result.success:
            self._users = list_result.data.get("users", [])
            self._refresh_list()
```

For card-style lists, the pattern is the same but with `Card` components from
`lib/ui/components/`. See [`lib/views/products.py`](../lib/views/products.py).

### 5.3 Navigation

Three ways to navigate, in order of preference:

**Simple API on `self.nav`** — for hand-written buttons:

```python
ft.ElevatedButton("Go Home", on_click=lambda e: self.nav.go("/"))
```

**`NavButton` component** — declarative, reusable:

```python
from lib.ui.components.nav_button import NavButton

NavButton("Open Login", "/login", self.nav_service)
```

**Path + query parameters** — read them from `self.params`:

```python
from pydantic import BaseModel

class ProductDetailView(BaseView):
    class Params(BaseModel):
        id: int                      # from /products/{id}
        tab: str = "overview"        # from ?tab=stock

    def build_content(self):
        p = self.params              # validated Pydantic model
        return ft.Text(f"Product {p.id}, tab={p.tab}")
```

The router merges `props["params"]` (path) and `props["query"]` (query string)
into `self.params` if you set a `Params` class. See
[`lib/views/product_detail.py`](../lib/views/product_detail.py).

To navigate **with** query params, build the URL yourself:

```python
self.nav.go(f"/products/{product_id}?tab=stock")
```

To register a parameterized route, edit `main.py`:

```python
router.register("/products/{id}", "lib.views.product_detail")
```

### 5.4 Loading States

For slow work, render placeholders first, then refresh once the data arrives.
The pattern lives in [`admin/databases.py`](../lib/views/admin/databases.py)
and [`admin/caches.py`](../lib/views/admin/caches.py):

```python
class DashboardView(BaseView):
    _status_cache: dict[str, dict] = {}    # class-level — survives navigation

    def build_content(self):
        body = ft.Column(spacing=10)

        def _fill_body():
            # Rebuild body controls from current cache state
            cards = self._make_cards()
            body.controls = [
                ft.Text("Status", size=24, weight=ft.FontWeight.BOLD),
                *cards,
                ft.TextButton("↺ Refresh", on_click=lambda e: _on_refresh()),
            ]

        async def _run_probe():
            # Slow work: probe every backend in parallel
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as ex:
                results = await loop.run_in_executor(
                    None, lambda: list(ex.map(self._probe, self._names()))
                )
            type(self)._status_cache.update(dict(zip(self._names(), results)))
            _fill_body()
            self.page.update()

        def _on_refresh():
            type(self)._status_cache.clear()
            _fill_body()
            self.page.update()
            self.page.run_task(_run_probe)

        _fill_body()                       # render placeholders immediately
        self.page.run_task(_run_probe)     # kick off the slow refresh
        return body
```

Key ideas:

- **Class-level cache** — `_status_cache` survives navigation, so the second visit shows cached results instantly.
- **Render twice** — first with placeholders, then with real data when the async task finishes.
- **`page.run_task`** — schedules the coroutine on Flet's event loop without blocking.

For a manual loading spinner pattern:

```python
class SlowUserDetailView(BaseView):
    class Params(BaseModel):
        id: str

    def build_content(self):
        self._content = ft.Container(
            content=ft.ProgressRing(),     # spinner while we wait
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

        async def _load():
            result = self.props["user_service"].execute(
                ActionRequest(action="get", data={"id": self.params.id})
            )
            if result.success:
                user = result.data
                self._content.content = ft.Text(
                    f"{user['username']} ({user['email']})"
                )
            else:
                self._content.content = ft.Text(result.error, color=ft.Colors.RED_400)
            self._content.update()

        self.page.run_task(_load)
        return self._content
```

### 5.5 Admin Views and the Backend Adapter

Admin views access all data through `self.props["backend"]` — an `IBackendAdapter`
instance — instead of individual service props. This decouples the view from the
concrete implementation (Python services in dev, HTTP API in production):

```python
class ManageUsersView(ProtectedView):
    def __init__(self, page, props):
        super().__init__(page, props)
        self._backend = props.get("backend")

    def build_content(self):
        # Auth
        user = self._backend.current_user()   # dict or None

        # Users — paginated
        result = self._backend.list_users(page=1, page_size=20)
        # → {"items": [...], "total": N, "page": 1, "page_size": 20, "pages": N}

        self._backend.create_user({"username": "alice", "email": "alice@x.com", "password": "..."})
        self._backend.delete_user(user_id_str)   # str UUID

        # Roles
        self._backend.list_roles()              # → [{"id": "...", "name": "admin"}, ...]
        self._backend.create_role("editor")
        self._backend.delete_role(role_id_str)

        # Scheduler (read-only)
        jobs = self._backend.list_jobs()
        # → [{"id": "...", "func_name": "...", "trigger": "...", "next_run_time": ...}]
```

**Rules:**
- Admin views call `backend`, not services or repos directly
- Non-admin views (`HomeView`, `ProductsView`) continue using individual service props
- Guard against `backend is None` if the primary DB might be unavailable at startup

**Interface:** `IBackendAdapter` is defined in `lib/adapters/backend_adapter.py`.
To add a new backend operation (e.g. `pause_job`), add it to the ABC and implement
it in `ServiceBackendAdapter` — view code is unchanged.

### 5.6 Auth-Gated Content in Public Views

Some views are public (no login required) but show extra controls when the user
is logged in — for example, an edit form on a product detail page. Check
`backend.auth.current_user()` in `__init__` and use it in `build_content()`:

```python
class ProductDetailView(BaseView):
    def __init__(self, page, props):
        super().__init__(page, props)
        self._service = props.get("product_service")
        backend = props.get("backend")
        self._is_admin = backend is not None and backend.auth.current_user() is not None

        # Pre-declare edit form fields so handlers can reference them
        self._edit_name: ft.TextField | None = None
        self._edit_status: ft.Text | None = None

    def _on_save(self, _e):
        result = self._service.execute(ActionRequest(action="update", data={
            "id": self.params.id,
            "name": self._edit_name.value.strip(),
        }))
        self._edit_status.value = "Saved." if result.success else f"Error: {result.error}"
        self._edit_status.color = ft.Colors.GREEN_400 if result.success else ft.Colors.RED_400
        self.page.update()

    def build_content(self):
        result = self._service.execute(ActionRequest(action="get", data={"id": self.params.id}))
        if not result.success:
            return ft.Text("Not found", color=ft.Colors.RED_400)

        p = result.data
        controls = [ft.Text(p["name"], size=28, weight=ft.FontWeight.BOLD)]

        if self._is_admin:
            # Edit section only visible when logged in
            self._edit_name = ft.TextField(label="Name", value=p["name"], width=280)
            self._edit_status = ft.Text("", size=12)
            controls += [
                ft.Divider(),
                ft.Text("Edit", size=18, weight=ft.FontWeight.BOLD),
                self._edit_name,
                ft.Row([
                    ft.ElevatedButton(content=ft.Text("Save"), on_click=self._on_save),
                    self._edit_status,
                ], spacing=10),
            ]

        return ft.Column(controls, spacing=15)
```

Key points:
- Resolve `is_admin` once in `__init__` — `build_content()` may run multiple times.
- Pre-declare mutable form fields on `self` before `build_content()` runs; the handler references them by attribute, not by closure.
- The edit section is rendered only when logged in — the public read portion always renders.

This differs from `ProtectedView` (which redirects to `/login` if not authenticated). Use auth-gated content when the view is genuinely public but offers richer features to logged-in users.

---

## Reference: View File Structure

The minimum view module:

```python
# lib/views/<page>.py
import flet as ft
from lib.ui.layouts.base_view import BaseView


class MyView(BaseView):
    title = "My Page"

    def build_content(self):
        return ft.Text("Hello")


def view(page: ft.Page, props: dict) -> ft.View:
    return MyView(page, props).render()
```

A view file is reached automatically by URL — `/my-page` loads
`lib/views/my_page.py`. No route registration needed unless you have path
params, in which case add one line to `main.py`:

```python
router.register("/users/{id}", "lib.views.user_detail")
```

Class-level toggles you can override:

| Attribute | Default | Purpose |
|---|---|---|
| `title` | `"FlexApp"` | Shown in the appbar. |
| `show_appbar` | `True` | Set `False` for fullscreen pages. |
| `show_sidebar` | `True` | Set `False` for login / standalone pages. |
| `show_bottombar` | `False` | Set `True` and override `build_bottombar`. |
| `Params` | `None` | A Pydantic `BaseModel` for typed path/query params. |

Overridable methods:

| Method | When to override |
|---|---|
| `build_content()` | **Always.** The page body. |
| `build_appbar()` | Custom app bar (defaults to `NavBar`). |
| `build_sidebar()` | Custom sidebar (defaults to `SideBar` with `SIDEBAR_ITEMS`). |
| `build_bottombar()` | Bottom nav. |

Read [`lib/ui/layouts/base_view.py`](../lib/ui/layouts/base_view.py) — the
whole base class is 127 lines.

---

## Checklist Before Committing a View

- [ ] Subclasses `BaseView` and exports `view(page, props)` at module level.
- [ ] Services come from `self.props` — no direct imports of service modules.
- [ ] Every `service.execute(...)` checks `result.success` before reading `result.data`.
- [ ] Event handlers either navigate, set state and call `page.update()`, or both.
- [ ] Slow work (network, DB probes) uses `self.page.run_task(...)`.
- [ ] Lambda handlers in loops capture loop variables with `lambda e, x=x: ...`.
- [ ] Empty states, error states, and success states all render readable UI.
- [ ] No business logic in the view — that belongs in the service.

If you're stuck, the reference implementations are:

- Simple read view: [`lib/views/home.py`](../lib/views/home.py)
- Form + navigation: [`lib/views/login.py`](../lib/views/login.py)
- List with detail: [`lib/views/products.py`](../lib/views/products.py) → [`lib/views/product_detail.py`](../lib/views/product_detail.py)
- Stateful view with multiple modes: [`lib/views/security.py`](../lib/views/security.py)
- Async loading + class-level cache: [`lib/views/admin/databases.py`](../lib/views/admin/databases.py)

That's the whole pattern. Build a view, wire its service into `main.py`, and
let the router pick it up by filename.
