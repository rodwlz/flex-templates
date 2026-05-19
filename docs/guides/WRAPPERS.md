---
title: "Service Wrapper Methods (Snap API)"
category: guide
audience: [developer, agent]
related:
  - ../core/CONTRACTS_GUIDE.md
  - VIEW_DEVELOPMENT.md
agent_priority: medium
---

# Wrappers — The Simple Snap API

Every major service in the framework follows the same three-layer pattern.
You only need to touch the top layer (the snap).

```
Model (pure logic)
  └── Service (ActionRequest / ActionResult contract)
        └── Wrapper (clean Python methods)  ← you use this
```

The two layers underneath never change. The wrapper is just a thin translation
layer so you never have to write `ActionRequest(action="...", data={...})` in
your own code.

---

## The Four Snaps

All four are injected automatically into every view via `BaseView`:

```python
self.nav     # navigate between pages
self.vault   # read/write encrypted secrets
self.events  # publish and subscribe to events

# Also available for lower-level access if needed:
self.nav_service
self.vault_service
```

---

## `nav` — Navigation

```python
self.nav.go("/login")           # push a new page
self.nav.go(f"/products/{id}")  # path params work too
self.nav.back()                 # go back one step
self.nav.forward()              # go forward
self.nav.back(steps=2)          # jump back two steps
self.nav.clear()                # reset history

self.nav.current                # "/current-url"
self.nav.can_go_back            # bool
self.nav.can_go_forward         # bool
```

**In a button:**
```python
ft.ElevatedButton(
    "Go to Login",
    on_click=lambda _: self.nav.go("/login"),
)
```

**Source:** [lib/services/nav.py](../lib/services/nav.py)
**Under the hood:** `NavigationService` → `EventBus` → `FletNavigationAdapter`

---

## `vault` — Secrets

```python
user   = self.vault.get("POSTGRES_USER")          # raises if locked/missing
host   = self.vault.get("DB_HOST", "localhost")   # returns default if missing
keys   = self.vault.keys()                        # ["POSTGRES_USER", "DB_HOST"]

self.vault.set("API_KEY", "sk_live_abc")          # write to memory
self.vault.delete("OLD_KEY")                      # remove from memory
self.vault.save()                                 # persist to .secrets/vault.json
self.vault.lock()                                 # clear from RAM

self.vault.is_locked                              # bool
```

**In a service:**
```python
class DatabaseService(SimpleService):
    def connect(self, data: dict) -> dict:
        url = f"postgresql://{self.vault.get('POSTGRES_USER')}:" \
              f"{self.vault.get('POSTGRES_PASSWORD')}@localhost/mydb"
        # connect...
        return {"connected": True}
```

**Source:** [lib/security/vault.py](../lib/security/vault.py)
**Under the hood:** `VaultService` → `crypto.py` → `VaultStore`

---

## `events` — Pub/Sub

```python
# Subscribe — attach a listener
self.events.on("order.placed", self._on_order_placed)

# Emit — fire an event from anywhere
self.events.emit("order.placed", {"order_id": 42, "total": 99.99})

# Unsubscribe — detach a listener
self.events.off("order.placed", self._on_order_placed)
```

**Example — a service that emits on success:**
```python
class OrderService(SimpleService):
    def __init__(self, events):
        self._events = events

    def place(self, data: dict) -> dict:
        order_id = db.insert(data)
        self._events.emit("order.placed", {"order_id": order_id})
        return {"order_id": order_id}
```

**Example — a view that reacts:**
```python
class DashboardView(BaseView):
    def __init__(self, page, props):
        super().__init__(page, props)
        self.events.on("order.placed", self._refresh)

    def _refresh(self, event):
        order_id = event.payload["order_id"]
        # update UI...
```

**Source:** [lib/core/events.py](../lib/core/events.py)
**Under the hood:** `EventBus` with subscribe/publish/unsubscribe

---

## `SimpleService` — Build Services Without Boilerplate

Instead of writing a match statement for every action, subclass `SimpleService`
and name your methods after the actions:

```python
# Before — full IService boilerplate
class OrderService(IService):
    def execute(self, request: ActionRequest) -> ActionResult:
        match request.action:
            case "place":  return self._place(request.data)
            case "cancel": return self._cancel(request.data)
            case _: return ActionResult(success=False, error=f"Unknown: {request.action}")

    def _place(self, data): ...
    def _cancel(self, data): ...


# After — just write the methods
class OrderService(SimpleService):
    def place(self, data: dict) -> dict:
        order_id = db.insert(data)
        return {"order_id": order_id}

    def cancel(self, data: dict) -> dict:
        db.delete(data["order_id"])
        return {}
```

**Rules:**
- Method name = action name (e.g. `def place` handles `action="place"`)
- Return a `dict` → auto-wrapped to `ActionResult(success=True, data={...})`
- Return an `ActionResult` directly for full control
- Raise any exception → auto-caught as `ActionResult(success=False, error=...)`
- Methods starting with `_` are private — never callable as actions

**Callers don't change.** `SimpleService` still satisfies `IService`, so
anything that calls `service.execute(ActionRequest(...))` works without modification.

**Source:** [lib/core/interfaces.py](../lib/core/interfaces.py)

---

## Full Example — A View Using All Three Snaps

```python
# lib/views/orders.py
import flet as ft
from lib.ui.layouts.base_view import BaseView
from lib.core.interfaces import SimpleService


class OrderService(SimpleService):
    def __init__(self, vault):
        self._api_key = vault.get("ORDERS_API_KEY")

    def fetch(self, data: dict) -> dict:
        import requests
        resp = requests.get(
            "https://api.example.com/orders",
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        return {"orders": resp.json()}


class OrdersView(BaseView):
    title = "Orders"

    def __init__(self, page, props):
        super().__init__(page, props)
        self._service = OrderService(self.vault)
        # React to new orders from any part of the app
        self.events.on("order.placed", lambda e: self._refresh_list())

    def _go_to_order(self, order_id):
        self.nav.go(f"/orders/{order_id}")

    def _refresh_list(self):
        result = self._service.execute(ActionRequest(action="fetch", data={}))
        if result.success:
            # rebuild UI with result.data["orders"]
            pass

    def build_content(self):
        return ft.Column([
            ft.Text("Orders", size=18, weight="bold"),
            ft.ElevatedButton("New Order", on_click=lambda _: self.nav.go("/orders/new")),
        ])


def view(page, props):
    return OrdersView(page, props).render()
```

---

## Pattern Summary

```
┌─────────────────────────────────────────┐
│  Your view / service                    │
│  self.nav.go("/page")                   │
│  self.vault.get("KEY")                  │
│  self.events.emit("thing.happened", {}) │
└────────────────┬────────────────────────┘
                 │  thin wrapper
┌────────────────▼────────────────────────┐
│  Nav / Vault / Events                   │
│  Translates clean calls to              │
│  ActionRequest / Event objects          │
└────────────────┬────────────────────────┘
                 │  contract layer
┌────────────────▼────────────────────────┐
│  NavigationService / VaultService /     │
│  EventBus                               │
│  Pure logic — no UI, no framework       │
└────────────────┬────────────────────────┘
                 │  infrastructure
┌────────────────▼────────────────────────┐
│  FletNavigationAdapter / VaultStore /   │
│  crypto.py                              │
│  Framework / file system details        │
└─────────────────────────────────────────┘
```

Swap any layer without touching the others.
