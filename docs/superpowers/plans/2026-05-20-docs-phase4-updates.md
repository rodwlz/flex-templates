# Phase 4 Docs Update — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring all documentation (MD sources + HTML interactive docs) in sync with Phase 4 additions: BackendAdapter layer, ProtectedView auth guard, migration workflow, new manage/scheduler routes, and the DATABASE_POSTGRES convention change.

**Architecture:** Three MD source files are updated/created first, then their HTML counterparts in `docs/api-docs/` are updated to match. The HTML files are static pages with a shared `css/docs.css` and `js/script.js`; no build step. `architecture.html` is a complete rewrite — its current content came from the old `API_ARCHITECTURE_SUMMARY.md` and is entirely wrong relative to the current `ARCHITECTURE.md`.

**Tech Stack:** Markdown, HTML5, Prism.js (CDN), vanilla JS. No build tools.

---

## Files to Create / Modify

| File | Action | Notes |
|---|---|---|
| `docs/core/ARCHITECTURE.md` | Modify | Add BackendAdapter section, fix vault sentence, update file tour, fix test count |
| `docs/guides/VIEW_DEVELOPMENT.md` | Modify | Add `backend` to props table; add ProtectedView section (2.4); add Backend Adapter section (5.5) |
| `docs/reference/MIGRATIONS.md` | Create | Full migration workflow reference |
| `docs/api-docs/architecture.html` | Rewrite | Replace old API-summary content with content from current ARCHITECTURE.md |
| `docs/api-docs/view-development.html` | Modify | Add `backend` table row; add ProtectedView and Backend Adapter HTML sections |
| `docs/api-docs/migrations.html` | Create | HTML counterpart of MIGRATIONS.md |
| `docs/api-docs/index.html` | Modify | Add Migrations card to the Reference section |

---

## Task 1: Update `docs/core/ARCHITECTURE.md`

**Files:**
- Modify: `docs/core/ARCHITECTURE.md`

Four targeted changes. No test — verify by reading the rendered file and checking all four patches are present.

- [ ] **Step 1: Fix the stale Vault paragraph**

In the `### Vault — \`lib/security/\`` section, the current text says:

```
`main.py` unlocks it at startup; services read secrets via `vault.get("KEY")`.
```

Replace that sentence with:

```
Vault starts **locked** — no auto-unlock at startup. The user unlocks it manually
via the `/security` view. After unlock, `main.py` wires vault-sourced DB and cache
connections via the `vault.unlocked` event. Deep dive: [VAULT_USAGE.md](../reference/VAULT_USAGE.md).
```

- [ ] **Step 2: Add BackendAdapter to "The core pieces"**

After the `### Router & BaseView` section, insert a new section. Find the line:

```markdown
### Vault — `lib/security/`
```

Insert this block immediately before it:

```markdown
### BackendAdapter — `lib/adapters/backend_adapter.py`

The plug between Flet views and the backend. Admin views call
`self.props["backend"]` — an `IBackendAdapter` instance — for all auth and
data operations. `ServiceBackendAdapter` is the concrete implementation (calls
Python services directly). Swap it for `HttpBackendAdapter` in `main.py` and no
view changes:

```python
class ManageUsersView(ProtectedView):
    def build_content(self):
        backend = self.props["backend"]
        users = backend.list_users(page=1, page_size=20)
```

`IBackendAdapter` defines: `login`/`logout`/`current_user`, `list_users`/`create_user`/
`delete_user`, `list_roles`/`create_role`/`delete_role`/`assign_role`/`remove_role`,
`list_jobs`.

`ProtectedView(BaseView)` is the auth-guard subclass — it checks
`backend.current_user()` before rendering and redirects to `/login` if the session
is empty.

```

- [ ] **Step 3: Update the Router & BaseView section**

In the `### Router & BaseView` section, find the sentence:

```
`BaseView` is the page template — every view subclasses it and only writes
`build_content()`.
```

Append after that sentence (before the code block):

```
Admin views that require login subclass `ProtectedView(BaseView)` instead. The
auth check is automatic — redirect to `/login` if `backend.current_user()` is None.
```

- [ ] **Step 4: Update the File Tour table**

Find the row:

```
| `lib/views/admin/databases.py` | Admin DB inspector — see this for the props pattern |
```

Insert these rows immediately after it (before `lib/views/admin/caches.py`):

```markdown
| `lib/adapters/backend_adapter.py` | `IBackendAdapter` ABC + `ServiceBackendAdapter` |
| `lib/ui/layouts/protected_view.py` | `ProtectedView` — auth guard, redirects to `/login` |
| `lib/views/login.py` | Login form — calls `backend.login()`, navigates on success |
| `lib/views/manage/users.py` | Paginated user list + create + delete (auth required) |
| `lib/views/manage/roles.py` | Role list + create + delete (auth required) |
| `lib/views/admin/scheduler.py` | Read-only APScheduler job inspector (auth required) |
| `lib/database/migrations/` | Alembic migration scripts — run `alembic upgrade head` |
```

- [ ] **Step 5: Fix the stale test count**

Find:

```
All 373 tests run on in-memory SQLite
```

Change to:

```
All 398 tests run on in-memory SQLite
```

- [ ] **Step 6: Commit**

```bash
git add docs/core/ARCHITECTURE.md
git commit -m "docs: update ARCHITECTURE.md for Phase 4 — BackendAdapter, ProtectedView, migrations, vault fix"
```

---

## Task 2: Update `docs/guides/VIEW_DEVELOPMENT.md`

**Files:**
- Modify: `docs/guides/VIEW_DEVELOPMENT.md`

Three changes: add a `backend` row to the props table, add a ProtectedView section, add a Backend Adapter section.

- [ ] **Step 1: Add `backend` to the props table**

Find the props table in section 2.2. It currently ends with:

```markdown
| `dev_nav` | `bool` | Show the orange floating dev nav |
```

Insert this row immediately before that last row:

```markdown
| `backend` | `IBackendAdapter` | Auth + user/role/job CRUD for admin views |
```

- [ ] **Step 2: Add the ProtectedView section (2.4)**

Find the heading `### 2.3 Injection vs Hardcoding`. Insert a new section immediately **after** that entire section ends (just before the `---` that precedes section 3). The end of section 2.3 is:

```markdown
For everything else: if it has a constructor, it goes through props.
```

After that line, insert:

```markdown

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

```

- [ ] **Step 3: Add the Backend Adapter section (5.5)**

At the end of section 5 (Common Patterns), after section `5.4 Loading States` and
before the `---` that starts the "Reference: View File Structure" section, insert:

```markdown
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

```

- [ ] **Step 4: Commit**

```bash
git add docs/guides/VIEW_DEVELOPMENT.md
git commit -m "docs: add ProtectedView, backend adapter, and backend prop to VIEW_DEVELOPMENT.md"
```

---

## Task 3: Create `docs/reference/MIGRATIONS.md`

**Files:**
- Create: `docs/reference/MIGRATIONS.md`

- [ ] **Step 1: Create the file with full content**

Create `docs/reference/MIGRATIONS.md` with the following content:

```markdown
---
title: "Database Migrations"
category: reference
audience: [developer, agent]
related:
  - ../core/CONVENTIONS.md
  - ../guides/ADDING_STUFF.md
agent_priority: medium
---

# Database Migrations

FlexTemplates uses [Alembic](https://alembic.sqlalchemy.org/) for schema
versioning. Migrations live in `lib/database/migrations/versions/` and are
checked into git alongside the code that needs them.

---

## Quick Reference

```bash
# Apply all pending migrations (run this after every pull)
alembic upgrade head

# Generate a migration after adding/changing a model
alembic revision --autogenerate -m "add products table"
alembic upgrade head

# Roll back one step
alembic downgrade -1

# Show current revision
alembic current

# Show full history
alembic history --verbose
```

---

## How It Connects to the App

`alembic.ini` at the project root points to `lib/database/migrations/`.
`env.py` inside that folder resolves the target database URL in this order:

1. `DATABASE_URL` environment variable — highest priority (CI, Docker, production)
2. `DATABASE_NAME` environment variable — names a `ConnectionRegistry` entry when
   the app is already booted (e.g. `DATABASE_NAME=analytics alembic upgrade head`)
3. `sqlalchemy.url` in `alembic.ini` — dev fallback, defaults to `sqlite:///./dev.db`

`env.py` imports all models so Alembic can diff them against the live schema:

```python
import lib.models.user  # noqa: F401
import lib.models.role  # noqa: F401
# Add new model imports here when you add new models
```

---

## Dev Workflow (SQLite)

On startup, `main.py` automatically runs `alembic upgrade head` against
`dev.db` when the primary database is the SQLite fallback:

```python
# main.py (runs at startup if no postgres is registered)
alembic_cmd.upgrade(AlembicConfig("alembic.ini"), "head")
```

You never need to run `alembic upgrade head` manually in dev — just restart the
app. The first run creates `dev.db` and applies all migrations.

---

## Production / Postgres Workflow

Run migrations **before** starting the app. Wire it into your deploy pipeline:

```bash
# In your deploy script / CI step:
DATABASE_URL=postgresql://user:pass@host/db alembic upgrade head

# Then start the app:
python main.py   # or docker-compose up
```

The app will refuse to boot if the schema is behind — any ORM query against a
missing table raises `OperationalError` immediately.

---

## Adding a New Model

**Step 1 — Write the model:**

```python
# lib/models/product.py
import uuid
from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from lib.database.base import Base

class Product(Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
```

**Step 2 — Register the model in `env.py`:**

```python
# lib/database/migrations/env.py
import lib.models.user    # noqa: F401
import lib.models.role    # noqa: F401
import lib.models.product # noqa: F401  ← add this
```

**Step 3 — Generate the migration:**

```bash
alembic revision --autogenerate -m "add products table"
```

Alembic diffs `Base.metadata` against the live DB and writes a new file to
`lib/database/migrations/versions/`. Review it before committing — autogenerate
is not perfect (it misses some index types and custom constraints).

**Step 4 — Apply it:**

```bash
alembic upgrade head
```

**Step 5 — Commit both the model and the migration:**

```bash
git add lib/models/product.py lib/database/migrations/versions/
git commit -m "feat: add Product model and migration"
```

---

## Targeting a Different Database

```bash
# By URL (any environment):
DATABASE_URL=postgresql://user:pass@host/analytics alembic upgrade head

# By registry name (when app is booted and ConnectionRegistry is populated):
DATABASE_NAME=analytics alembic upgrade head
```

`DATABASE_NAME` is useful when running migrations against a secondary DB from
inside the app process (e.g. a management command that calls alembic
programmatically).

---

## Existing Migrations

| Revision | Description |
|---|---|
| `1002b8218db7` | Initial users table (id, username, email, password_hash, salt, status) |
| `f5baad507a72` | Add roles and user_roles tables (id, name, description; M:M join table) |

---

## Stamping an Existing Database

If you created the schema via `create_tables()` (e.g. an older dev.db), Alembic
won't know about it. Stamp the current revision to mark the DB as up-to-date:

```bash
alembic stamp head
```

Then run `alembic upgrade head` normally for any future migrations.

---

## Notes

- **Never edit a migration that has already been applied** to a shared database
  (staging, production). Create a new revision instead.
- **Always review autogenerated migrations** before applying — Alembic sometimes
  generates spurious `alter_column` ops for types it can't perfectly compare.
- **SQLite limitations** — SQLite doesn't support `ALTER TABLE ... DROP COLUMN`
  or most constraint changes. Alembic's batch mode handles this; see the
  [Alembic docs on SQLite](https://alembic.sqlalchemy.org/en/latest/batch.html)
  if you hit issues.
```

- [ ] **Step 2: Commit**

```bash
git add docs/reference/MIGRATIONS.md
git commit -m "docs: add MIGRATIONS.md reference — alembic workflow, model registration, multi-DB targeting"
```

---

## Task 4: Rewrite `docs/api-docs/architecture.html`

**Files:**
- Modify: `docs/api-docs/architecture.html`

The current content is from the old `API_ARCHITECTURE_SUMMARY.md` (321 tests, "Files Built", etc.) and is entirely wrong. Replace the full file with content derived from the current `docs/core/ARCHITECTURE.md`.

- [ ] **Step 1: Replace the entire file**

Write `docs/api-docs/architecture.html` with the following complete content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Architecture Overview — FlexTemplates Docs</title>
    <link rel="stylesheet" href="css/docs.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
</head>
<body>
    <header>
        <h1>Architecture Overview</h1>
        <p class="breadcrumb">Core Concepts &rsaquo; Architecture Overview</p>
    </header>
    <main>

        <p>FlexTemplates 2.0 is a forkable Python framework: a Flet desktop UI, a FastAPI
        HTTP backend, and a SQLAlchemy data layer, all sharing one process. Every layer talks
        to its neighbours through standardized Pydantic contracts, so any piece can be
        swapped without touching the rest.</p>

        <hr>

        <h2>The LEGO Pitch</h2>

        <ul>
            <li><strong>Plugs</strong> are Pydantic models &mdash; <code>ActionRequest</code>, <code>ActionResult</code>, <code>Event</code>.</li>
            <li><strong>Blocks</strong> are services with one job each &mdash; <code>NavigationService</code>, <code>VaultService</code>, <code>ConnectionTester</code>.</li>
            <li><strong>Builder</strong> is <code>main.py</code> &mdash; the only file that knows about concrete types.</li>
        </ul>

        <p>Swap any block, the rest of the system can't tell. That's the architecture in one sentence.</p>

        <hr>

        <h2>The Layer Stack</h2>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-text">main.py            ← wires everything (the only file that names concrete types)
  │
  ├── views/       ← Flet pages; receive services via props dict
  ├── api/routes/  ← FastAPI endpoints; receive services via Depends
  │
  ├── ui/          ← Flet building blocks (router, BaseView, components)
  │
  ├── services/    ← Business logic (NavigationService, VaultService, ...)
  ├── adapters/    ← Non-SQL backends (RedisAdapter, FileAdapter, BackendAdapter)
  │
  ├── auth/        ← JWT handler + RBAC dependencies
  ├── tasks/       ← APScheduler wrapper (TaskScheduler)
  │
  ├── repositories/← CRUD on ORM models
  ├── models/      ← SQLAlchemy ORM tables
  ├── database/    ← SessionFactory, ConnectionRegistry, UnitOfWork, migrations
  ├── security/    ← Vault (encrypted secrets store) + bcrypt helpers
  └── config/      ← AppConfig (pydantic-settings, reads .env)</code></pre>
        </div>

        <hr>

        <h2>How a Request Flows</h2>

        <h3>Clicking a nav button</h3>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-text">User clicks NavButton("Products", "/products")
  ↓
NavButton.on_click() fires
  ↓
nav_service.execute(ActionRequest(action="visit", data={"url": "/products"}))
  ↓
NavigationService updates history stack, publishes Event(type="nav.route_changed")
  ↓
EventBus dispatches to FletNavigationAdapter → page.go("/products")
  ↓
FletRouter.route_change(page):
  - lazy-loads lib.views.products
  - calls view(page, props) → ProductsView(page, props).render()
  ↓
ProductsView builds content, wrapped with appbar/sidebar by BaseView
  ↓
Router appends to page.views and calls page.update() → Flet repaints</code></pre>
        </div>

        <p><code>NavigationService</code> has no Flet import. <code>FletNavigationAdapter</code>
        is the one piece that does — swap it for a web adapter and nothing else changes.</p>

        <hr>

        <h2>The Core Pieces</h2>

        <h3>Contracts — <code>lib/contracts/base.py</code></h3>

        <p>Three Pydantic models, used everywhere:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python">class ActionRequest(BaseModel):
    action: str                      # "test", "visit", "set", "create"
    data: dict[str, Any] = {}

class ActionResult(BaseModel):
    success: bool
    data: dict[str, Any] = {}
    events: list[Event] = []
    error: str | None = None

class Event(BaseModel):
    type: str                        # "user.created", "nav.route_changed"
    payload: dict[str, Any] = {}</code></pre>
        </div>

        <h3>Services — <code>lib/services/</code></h3>

        <p>Every service implements <code>IService.execute(ActionRequest) &rarr; ActionResult</code>.
        Most subclass <code>SimpleService</code> and get free dispatch + exception trapping:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python">class ConnectionTester(SimpleService):
    def test(self, data: dict) -> dict:
        factory = ConnectionRegistry.get(data["name"])
        # ... probe and return dict; SimpleService wraps it in ActionResult</code></pre>
        </div>

        <h3>Registries — <code>ConnectionRegistry</code>, <code>CacheRegistry</code></h3>

        <p>Class-level singletons. <code>main.py</code> registers everything at startup:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python">ConnectionRegistry.get("postgres")     # returns a SessionFactory
CacheRegistry.get("redis")             # returns a RedisAdapter</code></pre>
        </div>

        <p>All SQL databases use the <code>DATABASE_&lt;NAME&gt;</code> convention
        (<code>DATABASE_POSTGRES</code> &rarr; <code>"postgres"</code>). The
        <code>PRIMARY_DATABASE</code> env var names which registered DB the backend adapter
        targets (default <code>"postgres"</code>).</p>

        <h3>BackendAdapter — <code>lib/adapters/backend_adapter.py</code></h3>

        <p>The plug between Flet admin views and the backend. Views call
        <code>self.props["backend"]</code> &mdash; an <code>IBackendAdapter</code> instance
        &mdash; for all auth and data operations. Swap <code>ServiceBackendAdapter</code>
        for <code>HttpBackendAdapter</code> in <code>main.py</code> and no view changes:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python">class ManageUsersView(ProtectedView):
    def build_content(self):
        backend = self.props["backend"]
        result = backend.list_users(page=1, page_size=20)
        # result: {"items": [...], "total": N, "page": 1, "page_size": 20, "pages": N}</code></pre>
        </div>

        <p><code>IBackendAdapter</code> defines: <code>login</code>/<code>logout</code>/<code>current_user</code>,
        <code>list_users</code>/<code>create_user</code>/<code>delete_user</code>,
        <code>list_roles</code>/<code>create_role</code>/<code>delete_role</code>/<code>assign_role</code>/<code>remove_role</code>,
        <code>list_jobs</code>.</p>

        <h3>Router &amp; BaseView — <code>lib/ui/</code></h3>

        <p><code>FletRouter</code> turns URLs into views. Two routing modes:</p>
        <ul>
            <li><strong>Convention:</strong> <code>/products</code> &rarr; <code>lib.views.products.view(page, props)</code></li>
            <li><strong>Named (for params):</strong> <code>router.register("/products/{id}", "lib.views.product_detail")</code></li>
        </ul>

        <p><code>BaseView</code> is the page template &mdash; every view subclasses it and only
        writes <code>build_content()</code>. Admin views that require login subclass
        <code>ProtectedView(BaseView)</code> instead &mdash; redirect to <code>/login</code>
        is automatic if <code>backend.current_user()</code> returns None.</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python">class ProductsView(BaseView):           # public view
    title = "Products"
    show_sidebar = True
    def build_content(self):
        return ft.Column([ft.Text("Product list")])

class ManageUsersView(ProtectedView):   # auth-guarded view
    title = "Manage Users"
    def build_content(self):
        backend = self.props["backend"]
        ...</code></pre>
        </div>

        <h3>Vault — <code>lib/security/</code></h3>

        <p>Encrypted secrets store with a two-key design (master + confirm). Vault starts
        <strong>locked</strong> &mdash; no auto-unlock at startup. The user unlocks via the
        <code>/security</code> view. After unlock, <code>main.py</code> wires vault-sourced
        DB and cache connections via the <code>vault.unlocked</code> event.</p>

        <h3>API Server — <code>lib/api/</code></h3>

        <p><code>BackendServer</code> runs Uvicorn in a daemon thread, sharing the same
        Python process and same <code>ConnectionRegistry</code> as the Flet UI. Routes
        auto-discover from <code>lib/api/routes/</code>.</p>

        <h3>Migrations — <code>lib/database/migrations/</code></h3>

        <p>Alembic manages schema versioning. In dev, <code>main.py</code> runs
        <code>alembic upgrade head</code> automatically at startup. In production, run it
        in your deploy pipeline before starting the app:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-bash">DATABASE_URL=postgresql://user:pass@host/db alembic upgrade head</code></pre>
        </div>

        <hr>

        <h2>Where to Go for What</h2>

        <table>
            <thead>
                <tr><th>You want to&hellip;</th><th>Read</th></tr>
            </thead>
            <tbody>
                <tr><td>Add a new SQL DB / cache / view / service</td><td><code>docs/guides/ADDING_STUFF.md</code></td></tr>
                <tr><td>Build a Flet view</td><td><code>docs/guides/VIEW_DEVELOPMENT.md</code></td></tr>
                <tr><td>Build a protected (auth-guarded) view</td><td><code>docs/guides/VIEW_DEVELOPMENT.md §2.4</code></td></tr>
                <tr><td>Build an API endpoint</td><td><code>docs/guides/API_DEVELOPMENT.md</code></td></tr>
                <tr><td>Run or write a migration</td><td><code>docs/reference/MIGRATIONS.md</code></td></tr>
                <tr><td>Manage secrets</td><td><code>docs/reference/VAULT_USAGE.md</code></td></tr>
                <tr><td>Understand the naming / import rules</td><td><code>docs/core/CONVENTIONS.md</code></td></tr>
                <tr><td>Deploy with Docker / API-only mode</td><td><code>docs/guides/ONBOARDING_DEPLOYMENT.md</code></td></tr>
                <tr><td>Write tests</td><td><code>docs/reference/TESTING.md</code></td></tr>
            </tbody>
        </table>

        <hr>

        <h2>Key File Tour</h2>

        <table>
            <thead>
                <tr><th>File</th><th>Purpose</th></tr>
            </thead>
            <tbody>
                <tr><td><code>lib/contracts/base.py</code></td><td><code>ActionRequest</code>, <code>ActionResult</code>, <code>Event</code></td></tr>
                <tr><td><code>lib/core/interfaces.py</code></td><td><code>IService</code>, <code>SimpleService</code>, <code>StagingService</code></td></tr>
                <tr><td><code>lib/core/events.py</code></td><td><code>EventBus</code> (pub/sub)</td></tr>
                <tr><td><code>lib/config/settings.py</code></td><td><code>AppConfig</code> — env vars + <code>.env</code></td></tr>
                <tr><td><code>lib/database/session.py</code></td><td><code>SessionFactory</code>, <code>ConnectionRegistry</code></td></tr>
                <tr><td><code>lib/database/uow.py</code></td><td><code>UnitOfWork</code> — stage/preview/commit</td></tr>
                <tr><td><code>lib/database/migrations/</code></td><td>Alembic scripts — run <code>alembic upgrade head</code></td></tr>
                <tr><td><code>lib/models/user.py</code></td><td>Example ORM model with M:M roles relationship</td></tr>
                <tr><td><code>lib/models/role.py</code></td><td>Role ORM model</td></tr>
                <tr><td><code>lib/repositories/base.py</code></td><td><code>AbstractRepository[T]</code> — generic CRUD</td></tr>
                <tr><td><code>lib/adapters/backend_adapter.py</code></td><td><code>IBackendAdapter</code> ABC + <code>ServiceBackendAdapter</code></td></tr>
                <tr><td><code>lib/adapters/redis_adapter.py</code></td><td>Redis connector</td></tr>
                <tr><td><code>lib/adapters/file_adapter.py</code></td><td>CSV/JSON/Parquet/Excel reader</td></tr>
                <tr><td><code>lib/security/vault_service.py</code></td><td>Encrypted-secrets service</td></tr>
                <tr><td><code>lib/auth/jwt_handler.py</code></td><td><code>create_token()</code> / <code>decode_token()</code> — HS256 JWT</td></tr>
                <tr><td><code>lib/auth/dependencies.py</code></td><td><code>get_current_user</code> + <code>require_roles()</code> FastAPI deps</td></tr>
                <tr><td><code>lib/tasks/scheduler.py</code></td><td><code>TaskScheduler</code> — APScheduler wrapper</td></tr>
                <tr><td><code>lib/api/server.py</code></td><td><code>BackendServer</code> — Uvicorn in a daemon thread</td></tr>
                <tr><td><code>lib/api/mount_service.py</code></td><td>Auto-generates POST routes from a <code>SimpleService</code></td></tr>
                <tr><td><code>lib/ui/router.py</code></td><td><code>FletRouter</code> (URL &rarr; view)</td></tr>
                <tr><td><code>lib/ui/layouts/base_view.py</code></td><td><code>BaseView</code> page template</td></tr>
                <tr><td><code>lib/ui/layouts/protected_view.py</code></td><td><code>ProtectedView</code> — auth guard, redirects to <code>/login</code></td></tr>
                <tr><td><code>lib/views/login.py</code></td><td>Login form — calls <code>backend.login()</code></td></tr>
                <tr><td><code>lib/views/manage/users.py</code></td><td>Paginated user list + create + delete (auth required)</td></tr>
                <tr><td><code>lib/views/manage/roles.py</code></td><td>Role list + create + delete (auth required)</td></tr>
                <tr><td><code>lib/views/admin/scheduler.py</code></td><td>Read-only APScheduler job inspector (auth required)</td></tr>
                <tr><td><code>lib/views/admin/databases.py</code></td><td>Admin DB inspector — see this for the props pattern</td></tr>
                <tr><td><code>main.py</code></td><td>Boot sequence — only file that names concrete types</td></tr>
            </tbody>
        </table>

        <hr>

        <h2>Testing</h2>

        <p>All 398 tests run on in-memory SQLite and a <code>FakePage</code> stand-in for
        <code>ft.Page</code>, so the suite has no external dependencies and finishes in ~10 seconds.</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-bash">pytest tests/ -q              # run the full suite
pytest tests/ -k "backend"    # run only backend adapter tests</code></pre>
        </div>

        <hr>

        <h2>Async in Flet — the Short Version</h2>

        <p>Most event handlers are plain sync functions. When you need async (network probe,
        file I/O), use <code>page.run_task(coro)</code> &mdash; schedules a coroutine on
        Flet's event loop without blocking the UI. See
        <code>lib/views/admin/databases.py</code> for the full pattern.</p>

    </main>

    <nav class="page-nav">
        <div class="nav-group">
            <button class="btn-secondary" onclick="window.location.href='index.html'">&larr; Back to Hub</button>
            <button class="btn-secondary" disabled>&larr; Previous</button>
        </div>
        <span class="progress">Core Concepts &middot; 1 of 3</span>
        <div class="nav-group">
            <button class="btn-primary" onclick="window.location.href='template.html'">Pattern Template &rarr;</button>
        </div>
    </nav>

    <script src="js/script.js"></script>
</body>
</html>
```

- [ ] **Step 2: Open in browser and verify**

Open `docs/api-docs/architecture.html` in a browser. Check:
- Title shows "Architecture Overview"
- LEGO pitch section appears
- Layer stack code block renders with copy button
- BackendAdapter section appears under "The Core Pieces"
- File tour table shows `protected_view.py`, `backend_adapter.py`, `manage/users.py`
- Test count shows 398
- Previous/Next navigation: Previous disabled, Next goes to `template.html`

- [ ] **Step 3: Commit**

```bash
git add docs/api-docs/architecture.html
git commit -m "docs: rewrite architecture.html to match current ARCHITECTURE.md (Phase 4 content)"
```

---

## Task 5: Update `docs/api-docs/view-development.html`

**Files:**
- Modify: `docs/api-docs/view-development.html`

Three targeted changes matching Tasks 1–3 of the MD update.

- [ ] **Step 1: Add `backend` row to the props table**

In the HTML file, find the table row (around line 225):

```html
                <tr>
                    <td><code>dev_nav</code></td>
                    <td><code>bool</code></td>
                    <td>Show the orange floating dev nav</td>
                </tr>
```

Insert this row immediately **before** it:

```html
                <tr>
                    <td><code>backend</code></td>
                    <td><code>IBackendAdapter</code></td>
                    <td>Auth + user/role/job CRUD for admin views</td>
                </tr>
```

- [ ] **Step 2: Add the ProtectedView section (2.4)**

Find the closing `</p>` of section 2.3 that ends with:

```html
        <p>For everything else: if it has a constructor, it goes through props.</p>

        <hr>

        <h2 id="calling-services-from-views">
```

Insert the new section between that paragraph and the `<hr>`:

```html
        <h3>2.4 Protected Views (Auth Guard)</h3>

        <p>Views that require login subclass <code>ProtectedView</code> instead of
        <code>BaseView</code>. The redirect to <code>/login</code> is automatic &mdash;
        no manual check needed in <code>build_content</code>:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python">from lib.ui.layouts.protected_view import ProtectedView

class ManageUsersView(ProtectedView):    # auth check is automatic
    title = "Manage Users"
    show_sidebar = True

    def build_content(self):
        backend = self.props["backend"]
        result = backend.list_users(page=1, page_size=20)
        ...</code></pre>
        </div>

        <p><code>ProtectedView.render()</code> checks <code>backend.current_user()</code>
        before calling <code>super().render()</code>. If <code>current_user()</code>
        returns <code>None</code>, it redirects to <code>/login</code> and returns an
        empty view.</p>

        <p><strong>When to subclass <code>ProtectedView</code>:</strong> any admin or
        management view (user management, roles, scheduler, security, databases, caches).</p>

        <p><strong>When to stay on <code>BaseView</code>:</strong> <code>/login</code>
        itself, and all public pages (<code>/</code>, <code>/products</code>,
        <code>/not_found</code>).</p>

        <p><strong>Current protected views:</strong> <code>SecurityView</code>,
        <code>ManageUsersView</code>, <code>ManageRolesView</code>,
        <code>AdminSchedulerView</code>, <code>AdminDatabasesView</code>,
        <code>AdminCachesView</code>.</p>

```

- [ ] **Step 3: Add the Backend Adapter section (5.5)**

Find the `<hr>` that comes just before the "Reference: View File Structure" heading:

```html
        <hr>

        <h2 id="reference-view-file-structure">Reference: View File Structure</h2>
```

Insert the new section immediately before that `<hr>`:

```html
        <h3 id="admin-views-and-the-backend-adapter">5.5 Admin Views and the Backend Adapter</h3>

        <p>Admin views access all data through <code>self.props["backend"]</code> &mdash; an
        <code>IBackendAdapter</code> instance &mdash; instead of individual service props.
        This decouples the view from whether data comes from Python services (dev) or a
        remote HTTP API (production):</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python">class ManageUsersView(ProtectedView):
    def __init__(self, page, props):
        super().__init__(page, props)
        self._backend = props.get("backend")

    def build_content(self):
        # Paginated user list
        result = self._backend.list_users(page=1, page_size=20)
        # → {"items": [...], "total": N, "page": 1, "page_size": 20, "pages": N}

        # Create / delete
        self._backend.create_user({"username": "alice", "email": "alice@x.com", "password": "..."})
        self._backend.delete_user(user_id_str)   # str UUID

        # Roles
        self._backend.list_roles()              # → [{"id": "...", "name": "admin"}]
        self._backend.create_role("editor")
        self._backend.delete_role(role_id_str)

        # Scheduler jobs (read-only)
        jobs = self._backend.list_jobs()
        # → [{"id": "...", "func_name": "...", "trigger": "...", "next_run_time": ...}]</code></pre>
        </div>

        <p><strong>Rules:</strong></p>
        <ul>
            <li>Admin views call <code>backend</code>, not services or repos directly.</li>
            <li>Non-admin views (<code>HomeView</code>, <code>ProductsView</code>) continue
            using individual service props.</li>
            <li>Guard against <code>backend is None</code> if the primary DB might be
            unavailable at startup.</li>
        </ul>

        <p><code>IBackendAdapter</code> is defined in
        <code>lib/adapters/backend_adapter.py</code>. To add a new backend operation,
        add it to the ABC and implement it in <code>ServiceBackendAdapter</code> &mdash;
        view code is unchanged.</p>

```

- [ ] **Step 4: Open in browser and verify**

Open `docs/api-docs/view-development.html`. Check:
- Props table has a `backend` row showing `IBackendAdapter`
- Section 2.4 "Protected Views (Auth Guard)" appears after 2.3
- Section 5.5 "Admin Views and the Backend Adapter" appears before the Reference section
- All copy buttons work

- [ ] **Step 5: Commit**

```bash
git add docs/api-docs/view-development.html
git commit -m "docs: add ProtectedView and BackendAdapter sections to view-development.html"
```

---

## Task 6: Create `docs/api-docs/migrations.html` and update `docs/api-docs/index.html`

**Files:**
- Create: `docs/api-docs/migrations.html`
- Modify: `docs/api-docs/index.html`

- [ ] **Step 1: Create `docs/api-docs/migrations.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database Migrations — FlexTemplates Docs</title>
    <link rel="stylesheet" href="css/docs.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
</head>
<body>
    <header>
        <h1>Database Migrations</h1>
        <p class="breadcrumb">Troubleshooting &amp; Reference &rsaquo; Database Migrations</p>
    </header>
    <main>

        <p>FlexTemplates uses <a href="https://alembic.sqlalchemy.org/" target="_blank">Alembic</a>
        for schema versioning. Migrations live in <code>lib/database/migrations/versions/</code>
        and are checked into git alongside the code that needs them.</p>

        <hr>

        <h2>Quick Reference</h2>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-bash"># Apply all pending migrations (run this after every pull)
alembic upgrade head

# Generate a migration after adding/changing a model
alembic revision --autogenerate -m "add products table"
alembic upgrade head

# Roll back one step
alembic downgrade -1

# Show current revision
alembic current

# Show full history
alembic history --verbose</code></pre>
        </div>

        <hr>

        <h2>Dev Workflow (SQLite)</h2>

        <p>On startup, <code>main.py</code> automatically runs <code>alembic upgrade head</code>
        against <code>dev.db</code> when the primary database is the SQLite fallback. You never
        need to run it manually in dev &mdash; just restart the app.</p>

        <hr>

        <h2>Production / Postgres Workflow</h2>

        <p>Run migrations <strong>before</strong> starting the app. Wire it into your deploy pipeline:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-bash"># In your deploy script / CI step:
DATABASE_URL=postgresql://user:pass@host/db alembic upgrade head

# Then start the app:
python main.py</code></pre>
        </div>

        <hr>

        <h2>Adding a New Model</h2>

        <h3>Step 1 — Write the model</h3>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python"># lib/models/product.py
import uuid
from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from lib.database.base import Base

class Product(Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)</code></pre>
        </div>

        <h3>Step 2 — Register in <code>env.py</code></h3>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python"># lib/database/migrations/env.py
import lib.models.user     # noqa: F401
import lib.models.role     # noqa: F401
import lib.models.product  # noqa: F401  ← add this</code></pre>
        </div>

        <h3>Step 3 — Generate and apply</h3>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-bash">alembic revision --autogenerate -m "add products table"
alembic upgrade head</code></pre>
        </div>

        <h3>Step 4 — Commit both files</h3>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-bash">git add lib/models/product.py lib/database/migrations/versions/
git commit -m "feat: add Product model and migration"</code></pre>
        </div>

        <hr>

        <h2>Targeting a Different Database</h2>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-bash"># By URL (any environment):
DATABASE_URL=postgresql://user:pass@host/analytics alembic upgrade head

# By registry name (when ConnectionRegistry is populated):
DATABASE_NAME=analytics alembic upgrade head</code></pre>
        </div>

        <hr>

        <h2>Existing Migrations</h2>

        <table>
            <thead>
                <tr><th>Revision</th><th>Description</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td><code>1002b8218db7</code></td>
                    <td>Initial users table (id, username, email, password_hash, salt, status)</td>
                </tr>
                <tr>
                    <td><code>f5baad507a72</code></td>
                    <td>Add roles and user_roles tables (M:M join table with CASCADE delete)</td>
                </tr>
            </tbody>
        </table>

        <hr>

        <h2>Stamping an Existing Database</h2>

        <p>If you created the schema via <code>create_tables()</code> (older <code>dev.db</code>),
        Alembic doesn't know about it. Stamp the current revision to mark the DB as up-to-date,
        then run normally for future migrations:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-bash">alembic stamp head
# Then future migrations work normally:
alembic upgrade head</code></pre>
        </div>

        <hr>

        <h2>Notes</h2>

        <ul>
            <li><strong>Never edit an applied migration</strong> on a shared database. Create a new revision instead.</li>
            <li><strong>Always review autogenerated migrations</strong> before applying &mdash; Alembic sometimes generates spurious <code>alter_column</code> ops.</li>
            <li><strong>SQLite limitations</strong> &mdash; SQLite doesn't support most <code>ALTER TABLE</code> ops. Alembic's batch mode handles this; see the Alembic SQLite docs if you hit issues.</li>
        </ul>

    </main>

    <nav class="page-nav">
        <div class="nav-group">
            <button class="btn-secondary" onclick="window.location.href='index.html'">&larr; Back to Hub</button>
            <button class="btn-secondary" onclick="window.location.href='troubleshooting.html'">&larr; Troubleshooting</button>
        </div>
        <span class="progress">Reference &middot; Migrations</span>
        <div class="nav-group">
            <button class="btn-primary" onclick="window.location.href='anti-patterns.html'">Anti-Patterns &rarr;</button>
        </div>
    </nav>

    <script src="js/script.js"></script>
</body>
</html>
```

- [ ] **Step 2: Add Migrations card to `docs/api-docs/index.html`**

In `index.html`, find the Reference section's closing `</div>` that comes after the Anti-Patterns card. The current section ends with:

```html
                    <a href="anti-patterns.html" class="card">
                        <h3>&#128683; Anti-Patterns</h3>
                        <p>15 patterns that break the architecture. Before/after code for every mistake, grouped by layer.</p>
                        <button class="btn-primary">Avoid Mistakes &#8594;</button>
                    </a>
                </div>
            </section>
```

Insert a new card between the Anti-Patterns card and the closing `</div>`:

```html
                    <a href="migrations.html" class="card">
                        <h3>&#128195; Database Migrations</h3>
                        <p>Alembic workflow: upgrade head, autogenerate, multi-DB targeting, adding new models, stamping existing DBs.</p>
                        <button class="btn-primary">Run Migrations &#8594;</button>
                    </a>
```

- [ ] **Step 3: Open both files in browser and verify**

Open `docs/api-docs/index.html`:
- Reference section shows three cards: Troubleshooting, Anti-Patterns, Database Migrations
- Clicking "Run Migrations" navigates to `migrations.html`

Open `docs/api-docs/migrations.html`:
- Quick reference bash block renders with copy button
- "Adding a New Model" section has 4 sub-steps
- Table shows both existing revisions
- Nav: Previous → troubleshooting.html, Next → anti-patterns.html

- [ ] **Step 4: Commit**

```bash
git add docs/api-docs/migrations.html docs/api-docs/index.html
git commit -m "docs: add migrations.html and index card for Alembic migration reference"
```

---

## Self-Review

**Spec coverage:**
- BackendAdapter in ARCHITECTURE.md → Task 1 ✓
- ProtectedView in ARCHITECTURE.md → Task 1 ✓
- Phase 4 file tour additions → Task 1 ✓
- Vault auto-unlock fix → Task 1 ✓
- `backend` in props table → Task 2 ✓
- ProtectedView section in VIEW_DEVELOPMENT.md → Task 2 ✓
- Backend Adapter section in VIEW_DEVELOPMENT.md → Task 2 ✓
- MIGRATIONS.md → Task 3 ✓
- architecture.html rewrite → Task 4 ✓
- view-development.html updates → Task 5 ✓
- migrations.html + index.html card → Task 6 ✓

**No placeholders detected.** All steps contain actual content (HTML, Markdown, shell commands).

**Type consistency:** All references to `IBackendAdapter`, `ServiceBackendAdapter`, `ProtectedView`, `backend.list_users()`, `backend.current_user()` are consistent with the actual code in `lib/adapters/backend_adapter.py` and `lib/ui/layouts/protected_view.py`.
