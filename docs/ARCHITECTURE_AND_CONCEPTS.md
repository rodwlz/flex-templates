# Architecture & Key Concepts

FlexTemplates 2.0 is built on **standardized I/O contracts** and **dependency injection**. Every piece is swappable because everything talks through the same plugs (Pydantic models).

---

## The Big Picture: LEGO Philosophy

Think of it like LEGO blocks:
- **Plugs** = Pydantic models (`ActionRequest`, `ActionResult`, `Event`) — the standardized interfaces
- **Blocks** = Services (NavigationService, etc.) — each does one job
- **Builder** = You write views and components that snap together via these contracts

If you swap out a piece (e.g., replace NavigationService with your own), everything still works because both speak the same contract language.

---

## Core Concepts

### 1. Contracts (The Plugs)

**Location:** `lib/contracts/base.py`

Every message in the system is one of three Pydantic models:

```python
class ActionRequest(BaseModel):
    action: str                    # What you want to do: "visit", "back", "create_user"
    data: dict[str, Any] = {}      # Payload: {"url": "/login", "steps": 2}

class ActionResult(BaseModel):
    success: bool                  # Did it work?
    data: dict[str, Any] = {}      # Response data
    events: list[Event] = []       # Side effects (see EventBus below)
    error: str | None = None       # Why it failed

class Event(BaseModel):
    type: str                      # What happened: "nav.route_changed", "user.created"
    payload: dict[str, Any] = {}   # Details
```

**Why?** Every service receives the same request shape, returns the same result shape. You can test services without Flet, mock them easily, and swap implementations.

---

### 2. EventBus (The Messenger)

**Location:** `lib/core/events.py`

A pub/sub system for cross-layer communication:

```python
# Subscribe to an event type
event_bus.subscribe("nav.route_changed", lambda event: print(f"Went to {event.payload['url']}"))

# Publish an event
event_bus.publish(Event(type="nav.route_changed", payload={"url": "/login"}))

# Unsubscribe
event_bus.unsubscribe("nav.route_changed", callback)
```

**Why?** NavigationService doesn't import Flet. It just publishes events. FletNavigationAdapter listens and calls `page.go()`. They're decoupled — swap the adapter, NavigationService never changes.

**Real example:** When you click a NavButton → calls NavigationService.execute() → fires event → FletAdapter listens → page updates. NavigationService has zero Flet imports.

---

### 3. NavigationService (The History Manager)

**Location:** `lib/services/navigation_service.py`

Pure Python history stack (back/forward). No Flet.

```python
# Go somewhere
nav_service.execute(ActionRequest(action="visit", data={"url": "/products"}))

# Go back (or back 3 steps)
nav_service.execute(ActionRequest(action="back", data={"steps": 1}))

# Peek without moving
print(nav_service.peek_prev)  # What's the previous URL?
print(nav_service.peek_next)  # What's ahead?

# Check state
print(nav_service.current)           # "/" 
print(nav_service.can_go_back)       # True/False
print(nav_service.back_stack)        # ["/", "/login", "/products"]
```

**What it publishes:** When you navigate, it fires `Event(type="nav.route_changed", payload=nav_state)` where nav_state includes the URL and stack state.

---

### 4. BaseView (The Page Template)

**Location:** `lib/ui/layouts/base_view.py`

Every page in your app subclasses this. It handles the layout (appbar, sidebar, content, etc.). You only write `build_content()`.

```python
from lib.ui.layouts.base_view import BaseView
import flet as ft

class ProductsView(BaseView):
    title = "Products"              # Shows in the appbar
    show_sidebar = True             # Toggle pieces on/off
    
    def build_content(self):        # REQUIRED — return what goes in the middle
        return ft.Column([
            ft.Text("Product List"),
            # ... your content
        ])

def view(page, props):              # Router entry point — always this signature
    return ProductsView(page, props).render()
```

**What you get automatically:**
- AppBar (title + back button if available)
- Sidebar (with links to Home, Login, Products)
- Bottom bar (if you set `show_bottombar = True`)
- Dev URL bar at the top (when `dev_nav: True` in main.py)

**Advanced: Typed Parameters**

Some views need URL params (like `/products/{id}`). Define a Pydantic model:

```python
from pydantic import BaseModel

class ProductParams(BaseModel):
    id: int
    tab: str = "overview"  # optional with default

class ProductDetailView(BaseView):
    title = "Product"
    Params = ProductParams      # Magic: path + query params auto-validate into self.params
    
    def build_content(self):
        product_id = self.params.id
        return ft.Text(f"Product {product_id}")
```

When you navigate to `/products/42?tab=reviews`, the router:
1. Extracts `id=42` from the path
2. Extracts `tab=reviews` from the query string
3. Merges them
4. Validates with your Pydantic model (crashes if `id` isn't an int)
5. Stores in `self.params`

---

### 5. FletRouter (The URL Dispatcher)

**Location:** `lib/ui/router.py`

Converts URLs to views. Two modes:

**Convention routing (zero config):**
```
/login       → lib.views.login
/products    → lib.views.products
/            → lib.views.home
```

**Named routing (explicit, for params):**
```python
router.register("/products/{id}", "lib.views.product_detail")
```

The router is called every time the URL changes:
1. Parse the URL path and query string
2. Match against registered routes (named first, then convention)
3. Lazy-load the view module
4. Call `view(page, props)` → get an `ft.View` back
5. Render it

**Caching:** Modules are cached after first load, so hot-reloading in dev works — change the file, the next navigation loads fresh code.

---

### 6. Async in Flet

**The short version:** Flet 0.84+ is built on async, but **you usually don't write async code**.

Here's what happened:
- **Flet 0.19** (your original) was sync. All event handlers were blocking.
- **Flet 0.84+** is async under the hood. Event loop runs in the background.
- **For you:** Just write normal Python. If you need to make network calls, use `httpx` with `.get()` not `.get_async()` (it blocks the UI thread, but for simple dev it's fine).

**When async matters:**

If you want to fetch data *without blocking the UI*, use `asyncio`:

```python
import asyncio
import httpx

async def load_data():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.example.com/products")
        return resp.json()

# In a button click handler:
async def on_load_click(e):
    data = await load_data()
    # Update UI
    my_text.value = str(data)
    my_text.update()
```

But Flet's event handlers aren't async by default. For now, stick with blocking `.get()` — it's simpler and fine for a learning project. When you hit performance issues, then optimize.

---

## What's Missing (You Can Add These)

### 1. **A Real Database Layer**

Currently there's no database. The architecture has:
- `lib/models/` (empty — where ORM models go)
- `lib/repositories/` (empty — where data access goes)
- `lib/database/` (empty — SQLAlchemy setup)

**What to add:**
1. Define a User ORM model in `lib/models/user.py`
2. Create a UserRepository in `lib/repositories/user_repository.py`
3. Create a UserService in `lib/services/user_service.py` that uses the repo
4. Wire it into the DI container (currently in [main.py](../main.py)'s props factory)
5. Use it from views

See `docs/ADDING_STUFF.md` for a step-by-step recipe.

### 2. **API Backend (FastAPI)**

The codebase imports FastAPI stuff but doesn't use it. You could:
1. Create `lib/api/server.py` to run Uvicorn in a background thread
2. Add routes in `lib/api/routes/users.py`, `products.py`, etc.
3. Wire the container to provide services to FastAPI
4. Call the API from views instead of having logic in the UI

This is optional — the app works fine as a pure Flet client.

### 3. **More Views**

Currently you have:
- Home
- Login (no form logic)
- Products (list)
- Product Detail (parameterized route demo)
- Not Found (404)

Add views for:
- User profile
- Settings
- Admin dashboard
- Search results
- Error pages (403, 500, etc.)

Each follows the BaseView pattern.

### 4. **Real Login Logic**

The Login view doesn't actually authenticate. Add:
1. A form with username/password fields
2. A UserService method `authenticate(username, password)` that checks credentials
3. Store the auth token (or user session) somewhere
4. Gate other views to require login

### 5. **Components You Haven't Made**

Common UI pieces missing:
- Form inputs (text field, dropdown, date picker)
- Data table (sortable, paginated)
- Modal dialogs
- Toast notifications
- Loading spinners
- Breadcrumbs

See `docs/ADDING_STUFF.md` recipe #2 for how to create a custom component.

---

## How Data Flows Through the System

### Example: Click "Products" Button → Navigate → Render New Page

```
User clicks NavButton("Products", "/products")
  ↓
NavButton.on_click() fires
  ↓
Calls: nav_service.execute(ActionRequest(action="visit", data={"url": "/products"}))
  ↓
NavigationService._visit() runs:
  - Appends "/products" to back_stack
  - Clears forward_stack
  - Publishes: Event(type="nav.route_changed", payload={...})
  ↓
EventBus dispatches to all subscribers
  ↓
FletNavigationAdapter (subscribed) sees the event:
  - Extracts the new URL
  - Calls: page.go("/products")
  ↓
Flet fires: page.on_route_change event
  ↓
Router.route_change(page) runs:
  - Parses "/products" → path, query strings
  - Calls _resolve() → matches convention route
  - Lazy-loads lib.views.products module
  - Calls: view(page, props) → ProductsView(page, props).render()
  ↓
ProductsView.render() builds the ft.View:
  - Calls build_content() → your Column of products
  - Wraps with appbar, sidebar, dev URL bar
  - Returns ft.View with all controls
  ↓
Router appends to page.views, calls page.update()
  ↓
Flet re-renders the screen
```

**Key insight:** NavigationService and FletRouter are decoupled. You could swap FletRouter for a web-based router, or swap NavigationService for something else — the contract stays the same.

---

## File Tour

| File | Purpose |
|---|---|
| `lib/contracts/base.py` | ActionRequest, ActionResult, Event — the plugs |
| `lib/core/events.py` | EventBus: pub/sub |
| `lib/core/interfaces.py` | ABC base classes (optional, for type hints) |
| `lib/services/navigation_service.py` | History stack, no Flet |
| `lib/ui/adapter.py` | FletNavigationAdapter: bridges events to page.go() |
| `lib/ui/router.py` | URL → view loader |
| `lib/ui/layouts/base_view.py` | Abstract page template |
| `lib/ui/components/nav_button.py`, etc. | Reusable UI bits |
| `lib/views/home.py`, `login.py`, etc. | Pages (each subclasses BaseView) |
| `main.py` | Boot sequence, wires everything together |

---

## Testing Strategy

Because contracts are Pydantic, you can test **services without Flet**:

```python
def test_back_button_works():
    event_bus = EventBus()
    nav = NavigationService(event_bus)
    
    # No Flet involved — pure Python
    nav.execute(ActionRequest(action="visit", data={"url": "/login"}))
    nav.execute(ActionRequest(action="back"))
    
    assert nav.current == "/"
```

Test views with a `FakePage` (in `tests/conftest.py`) — it records route changes without rendering:

```python
def test_login_route_renders():
    router = FletRouter(nav_service)
    page = FakePage("/login")
    
    router.route_change(page)
    
    assert len(page.views) == 1  # View was added
    assert page.update_count == 1  # Update was called
```

---

## Next Steps

1. **Read** `docs/ADDING_STUFF.md` — recipes for common tasks
2. **Pick one missing piece** — add a view, a component, or database layer
3. **Write a test first** — describe what you want, then implement
4. **Run `python run_test.py`** — make sure nothing broke
5. **Try it in the app** — type a URL in the dev bar, see your change

You've got the foundation. Now make it yours.
