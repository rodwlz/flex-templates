# Phase 5D — Documentation Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update all HTML and Markdown docs to reflect Phase 5C additions — `HttpBackendAdapter`, `/v1/` API versioning, four new endpoints, and domain sub-adapter architecture.

**Architecture:** HTML docs (`docs/api-docs/`) are what the developer reads in a browser; MD docs (`docs/`) are what agents read. Changes touch 9 existing HTML files, create 1 new HTML file (`http-mode.html`), modify 4 MD files, and delete 1 stale MD file. No Python code changes — `pytest tests/ -q` must still pass at every step.

**Tech Stack:** Hand-edited HTML/CSS (no build tool), Markdown, Prism.js for syntax highlighting (CDN).

---

## File Map

| File | Action |
|---|---|
| `docs/guides/API_DEVELOPMENT.md` | Modify — fix stale URLs, add /v1 note |
| `docs/core/ARCHITECTURE.md` | Modify — update BackendAdapter section |
| `docs/guides/EXTENDING_BACKEND.md` | Modify — update Step 5 |
| `docs/core/CONVENTIONS.md` | Modify — add /v1 convention |
| `docs/reference/API_ARCHITECTURE_SUMMARY.md` | Delete |
| `docs/api-docs/architecture.html` | Modify — expand Backend Adapter section |
| `docs/api-docs/api-development.html` | Modify — add live docs banner + new endpoints table |
| `docs/api-docs/http-mode.html` | Create — new page |
| `docs/api-docs/index.html` | Modify — add HTTP Mode card |
| `docs/api-docs/view-development.html` | Modify — update section 5.5 domain sub-adapter API |
| `docs/api-docs/decision-trees.html` | Modify — fix stale URL headings |
| `docs/api-docs/troubleshooting.html` | Modify — add HTTPS ValueError entry |
| `docs/api-docs/anti-patterns.html` | Modify — add IBackendAdapter anti-pattern |

---

## Task 1: Fix stale URLs in `docs/guides/API_DEVELOPMENT.md`

**Files:**
- Modify: `docs/guides/API_DEVELOPMENT.md`

- [ ] **Step 1: Add /v1 note before the first code example**

Find this exact text (just before the first `### The route` heading):

```
## Quick Example

A complete POST endpoint with validation, a service call, and error handling — all
in one place. This is the canonical shape every endpoint in the codebase follows.

### The route
```

Replace with:

```
## Quick Example

> **All routes are prefixed `/v1/`** — FastAPI `/docs` is the canonical reference for full request/response schemas.

A complete POST endpoint with validation, a service call, and error handling — all
in one place. This is the canonical shape every endpoint in the codebase follows.

### The route
```

- [ ] **Step 2: Fix first router prefix in Quick Example**

Find:
```python
router = APIRouter(prefix="/roles", tags=["roles"])
```
(This is the first occurrence, inside the Quick Example code block)

Replace with:
```python
router = APIRouter(prefix="/v1/roles", tags=["roles"])
```

Note: Use Edit with enough surrounding context to match only the first occurrence. The surrounding context is:
```python
from lib.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


def get_service() -> RoleService:
```

- [ ] **Step 3: Fix test URLs in "Testing happy paths" section**

Find this entire block:
```python
def test_post_role_creates_role(api_client):
    """POST /roles creates a role and returns it."""
    response = api_client.post("/roles", json={
        "name": "admin",
        "description": "Administrator",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "admin"
    assert data["description"] == "Administrator"
    assert "id" in data


def test_list_roles_returns_all(api_client):
    """GET /roles returns every created role."""
    api_client.post("/roles", json={"name": "admin", "description": "Admin"})
    api_client.post("/roles", json={"name": "editor", "description": "Editor"})

    response = api_client.get("/roles")
    assert response.status_code == 200
    assert len(response.json()["roles"]) == 2


def test_get_user_includes_roles_array(api_client):
    """GET /users/{id} returns the user with a roles field."""
    create_resp = api_client.post("/users", json={
        "username": "bob",
        "email": "bob@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })
    user_id = create_resp.json()["id"]

    response = api_client.get(f"/users/{user_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "bob"
    assert "roles" in body
    assert body["roles"] == []
```

Replace with:
```python
def test_post_role_creates_role(api_client):
    """POST /v1/roles creates a role and returns it."""
    response = api_client.post("/v1/roles", json={
        "name": "admin",
        "description": "Administrator",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "admin"
    assert data["description"] == "Administrator"
    assert "id" in data


def test_list_roles_returns_all(api_client):
    """GET /v1/roles returns every created role."""
    api_client.post("/v1/roles", json={"name": "admin", "description": "Admin"})
    api_client.post("/v1/roles", json={"name": "editor", "description": "Editor"})

    response = api_client.get("/v1/roles")
    assert response.status_code == 200
    assert len(response.json()["roles"]) == 2


def test_get_user_includes_roles_array(api_client):
    """GET /v1/users/{id} returns the user with a roles field."""
    create_resp = api_client.post("/v1/users", json={
        "username": "bob",
        "email": "bob@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })
    user_id = create_resp.json()["id"]

    response = api_client.get(f"/v1/users/{user_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "bob"
    assert "roles" in body
    assert body["roles"] == []
```

- [ ] **Step 4: Fix test URLs in "Testing error paths" section**

Find this entire block:
```python
def test_get_role_404_when_missing(api_client):
    """GET /roles/{id} with an unknown UUID returns 404."""
    import uuid
    response = api_client.get(f"/roles/{uuid.uuid4()}")
    assert response.status_code == 404


def test_delete_role_404_when_missing(api_client):
    """DELETE /roles/{id} returns 404 for a UUID that does not exist."""
    import uuid
    response = api_client.delete(f"/roles/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_user_404_on_malformed_uuid(api_client):
    """A non-UUID path segment surfaces as 404.

    The route parameter is typed `str`. The service calls `uuid.UUID(data['id'])`,
    which raises ValueError on a malformed string. SimpleService wraps that as
    ActionResult(success=False), and the route returns 404.
    """
    response = api_client.get("/users/not-a-uuid")
    assert response.status_code == 404


def test_get_user_404_detail_contains_id(api_client):
    """The 404 detail string includes the missing ID so the caller knows what went wrong."""
    import uuid
    missing_id = str(uuid.uuid4())
    response = api_client.get(f"/users/{missing_id}")
    assert response.status_code == 404
    assert missing_id in response.json()["detail"]
```

Replace with:
```python
def test_get_role_404_when_missing(api_client):
    """GET /v1/roles/{id} with an unknown UUID returns 404."""
    import uuid
    response = api_client.get(f"/v1/roles/{uuid.uuid4()}")
    assert response.status_code == 404


def test_delete_role_404_when_missing(api_client):
    """DELETE /v1/roles/{id} returns 404 for a UUID that does not exist."""
    import uuid
    response = api_client.delete(f"/v1/roles/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_user_404_on_malformed_uuid(api_client):
    """A non-UUID path segment surfaces as 404.

    The route parameter is typed `str`. The service calls `uuid.UUID(data['id'])`,
    which raises ValueError on a malformed string. SimpleService wraps that as
    ActionResult(success=False), and the route returns 404.
    """
    response = api_client.get("/v1/users/not-a-uuid")
    assert response.status_code == 404


def test_get_user_404_detail_contains_id(api_client):
    """The 404 detail string includes the missing ID so the caller knows what went wrong."""
    import uuid
    missing_id = str(uuid.uuid4())
    response = api_client.get(f"/v1/users/{missing_id}")
    assert response.status_code == 404
    assert missing_id in response.json()["detail"]
```

- [ ] **Step 5: Fix test URLs in "Testing validation failures" section**

Find:
```python
def test_create_user_400_on_missing_username(api_client):
    """POST /users without a username returns 400 (the service raises ValueError)."""
    response = api_client.post("/users", json={
        "email": "no-username@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })
    # Missing username causes a KeyError in the service, wrapped as success=False
    assert response.status_code == 400
```

Replace with:
```python
def test_create_user_400_on_missing_username(api_client):
    """POST /v1/users without a username returns 400 (the service raises ValueError)."""
    response = api_client.post("/v1/users", json={
        "email": "no-username@example.com",
        "password_hash": "hash",
        "salt": "salt",
    })
    # Missing username causes a KeyError in the service, wrapped as success=False
    assert response.status_code == 400
```

- [ ] **Step 6: Fix second router prefix in "Full CRUD" section**

Find:
```python
# lib/api/routes/roles.py  — complete CRUD example
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])
```

Replace with:
```python
# lib/api/routes/roles.py  — complete CRUD example
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lib.contracts.base import ActionRequest
from lib.database.session import ConnectionRegistry
from lib.services.role_service import RoleService

router = APIRouter(prefix="/v1/roles", tags=["roles"])
```

- [ ] **Step 7: Fix docstring in "Filtering" section**

Find:
```python
    """GET /users?skip=0&limit=10"""
```

Replace with:
```python
    """GET /v1/users?skip=0&limit=10"""
```

- [ ] **Step 8: Fix tokenUrl and auth/login reference**

Find:
```
(not JSON), because `OAuth2PasswordBearer` is wired with `tokenUrl="/auth/login"`:

```python
# lib/api/routes/auth.py  — already included in auto-discovery
POST /auth/login
```

Replace with:
```
(not JSON), because `OAuth2PasswordBearer` is wired with `tokenUrl="/v1/auth/login"`:

```python
# lib/api/routes/auth.py  — already included in auto-discovery
POST /v1/auth/login
```

- [ ] **Step 9: Run tests to verify no Python code was broken**

```bash
pytest tests/ -q
```

Expected: all tests pass (no Python code changed — this is a doc-only sanity check).

- [ ] **Step 10: Commit**

```bash
git add docs/guides/API_DEVELOPMENT.md
git commit -m "docs: fix stale route URLs in API_DEVELOPMENT.md (/roles → /v1/roles, etc.)"
```

---

## Task 2: Update `docs/core/ARCHITECTURE.md` — Backend Adapter section

**Files:**
- Modify: `docs/core/ARCHITECTURE.md`

- [ ] **Step 1: Replace the BackendAdapter subsection**

Find this exact block (the entire BackendAdapter subsection):
```
### BackendAdapter — `lib/adapters/backend_adapter.py`

The plug between Flet admin views and the backend. Admin views call
`self.props["backend"]` — an `IBackendAdapter` instance — for all auth and
data operations. `ServiceBackendAdapter` is the concrete implementation (calls
Python services directly). Swap it for `HttpBackendAdapter` in `main.py` and
no view changes:

```python
class ManageUsersView(ProtectedView):
    def build_content(self):
        backend = self.props["backend"]
        result = backend.list_users(page=1, page_size=20)
        # result: {"items": [...], "total": N, "page": 1, "page_size": 20, "pages": N}
```

`IBackendAdapter` defines: `login`/`logout`/`current_user`, `list_users`/`create_user`/
`delete_user`, `list_roles`/`create_role`/`delete_role`/`assign_role`/`remove_role`,
`list_jobs`.

`ProtectedView(BaseView)` is the auth-guard subclass — it checks
`backend.current_user()` before rendering and redirects to `/login` if the
session is empty.
```

Replace with:
```
### BackendAdapter — `lib/adapters/backend_adapter.py`

The plug between Flet admin views and the backend. `IBackendAdapter` exposes four
typed domain properties:

| Property | Interface | What it does |
|---|---|---|
| `backend.auth` | `IAuthAdapter` | `login()`, `logout()`, `current_user()` |
| `backend.users` | `IUserAdapter` | `list()`, `create()`, `delete()` |
| `backend.roles` | `IRoleAdapter` | `list()`, `create()`, `delete()`, `assign()`, `remove()` |
| `backend.scheduler` | `ISchedulerAdapter` | `list()` — read-only job inspector |

Two concrete implementations:

- **`ServiceBackendAdapter`** — in-process, calls Python services directly. Current default in `main.py`.
- **`HttpBackendAdapter`** — over HTTP, calls FastAPI `/v1/` endpoints. Drop-in replacement.

One-line swap in `main.py` switches the whole app:

```python
# In-process (default):
backend = ServiceBackendAdapter(factory, user_service, scheduler)

# HTTP (local or remote):
backend = HttpBackendAdapter(base_url="http://localhost:8080")
```

Both satisfy `IBackendAdapter`. Views never touch a URL — they call
`backend.auth.login()`, `backend.users.list()`, etc., and the concrete type
is an implementation detail of `main.py` only.

`ProtectedView(BaseView)` checks `backend.auth.current_user()` before rendering
and redirects to `/login` if the session is empty.
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add docs/core/ARCHITECTURE.md
git commit -m "docs: update BackendAdapter section in ARCHITECTURE.md for domain sub-adapters"
```

---

## Task 3: Update `docs/guides/EXTENDING_BACKEND.md` — Step 5

**Files:**
- Modify: `docs/guides/EXTENDING_BACKEND.md`

- [ ] **Step 1: Add HttpBackendAdapter note after Step 5**

Find this exact block (the end of Step 5):
```
And wire `OrderService` into `ServiceBackendAdapter.__init__`:

```python
def __init__(self, factory, user_service, scheduler, order_service=None):
    ...
    self._order_service = order_service or OrderService(factory)
```

---

## 6. Wire in `main.py`
```

Replace with:
```
And wire `OrderService` into `ServiceBackendAdapter.__init__`:

```python
def __init__(self, factory, user_service, scheduler, order_service=None):
    ...
    self._order_service = order_service or OrderService(factory)
```

> **If you also need HTTP support:** Add the same method to `HttpBackendAdapter`
> (`lib/adapters/http_backend_adapter.py`), wiring it to the corresponding `/v1/`
> endpoint. If the operation should be universally available regardless of adapter,
> add the abstract method to `IBackendAdapter` in `lib/adapters/backend_adapter.py` first.

---

## 6. Wire in `main.py`
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add docs/guides/EXTENDING_BACKEND.md
git commit -m "docs: add HttpBackendAdapter note to EXTENDING_BACKEND.md step 5"
```

---

## Task 4: Add `/v1` convention to `docs/core/CONVENTIONS.md`

**Files:**
- Modify: `docs/core/CONVENTIONS.md`

- [ ] **Step 1: Add /v1 convention section**

Find the line (end of file or near it, look for the last `---` separator and any trailing content). The file ends with several numbered sections. Add a new section after the last `---` divider in the file.

First, read the end of `CONVENTIONS.md` to find the correct insertion point. Then insert before the final line of the file:

Find (near the end of the file — the last `---` followed by a heading):
```
---

## 8.
```
(Note: find the actual last `---` + section heading in the file)

Actually, read the end of the file first to see what the last section is, then append the new section. The new content to append at the end of the file (before any trailing newline) is:

```markdown

---

## API Route Versioning — `/v1/` prefix

**All API routes use the `/v1/` prefix.** This is the universal contract that makes
`HttpBackendAdapter` work:

- `HttpBackendAdapter` calls `/v1/...` URLs — the adapter doesn't care whether it's
  talking to a local dev server or a remote production host.
- `ServiceBackendAdapter` bypasses HTTP entirely and calls Python methods directly —
  but the result is identical because both implement `IBackendAdapter`.
- Any external client (JS frontend, mobile app, CLI tool) targets the same `/v1/`
  prefix. Write the endpoint once, consume from anywhere.

**Never skip the prefix in route definitions or test URLs.** When breaking changes are
needed, add a `/v2/` router alongside `/v1/` rather than modifying existing routes. Old
clients keep working on `/v1/`; new clients adopt `/v2/`. No flag day, no breaking change.

```python
# CORRECT
router = APIRouter(prefix="/v1/roles", tags=["roles"])

# WRONG — HttpBackendAdapter will not find this route
router = APIRouter(prefix="/roles", tags=["roles"])
```
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add docs/core/CONVENTIONS.md
git commit -m "docs: add /v1 versioning convention to CONVENTIONS.md"
```

---

## Task 5: Delete `docs/reference/API_ARCHITECTURE_SUMMARY.md`

**Files:**
- Delete: `docs/reference/API_ARCHITECTURE_SUMMARY.md`

- [ ] **Step 1: Delete the file**

```bash
git rm docs/reference/API_ARCHITECTURE_SUMMARY.md
```

This file lists routes that are now maintained by FastAPI's `/docs`. Deleting removes a maintenance burden with no loss of information.

- [ ] **Step 2: Commit**

```bash
git commit -m "docs: delete API_ARCHITECTURE_SUMMARY.md — superseded by FastAPI live /docs"
```

---

## Task 6: Expand Backend Adapter section in `docs/api-docs/architecture.html`

**Files:**
- Modify: `docs/api-docs/architecture.html`

- [ ] **Step 1: Replace the BackendAdapter subsection**

Find this entire block (lines 147–165 approximately):
```html
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
```

Replace with:
```html
        <h3>BackendAdapter — <code>lib/adapters/backend_adapter.py</code></h3>

        <p>The plug between Flet admin views and the backend. <code>IBackendAdapter</code>
        exposes four typed domain properties — views call these, never a URL:</p>

        <table>
            <thead>
                <tr><th>Property</th><th>Interface</th><th>Methods</th></tr>
            </thead>
            <tbody>
                <tr><td><code>backend.auth</code></td><td><code>IAuthAdapter</code></td><td><code>login()</code>, <code>logout()</code>, <code>current_user()</code></td></tr>
                <tr><td><code>backend.users</code></td><td><code>IUserAdapter</code></td><td><code>list()</code>, <code>create()</code>, <code>delete()</code></td></tr>
                <tr><td><code>backend.roles</code></td><td><code>IRoleAdapter</code></td><td><code>list()</code>, <code>create()</code>, <code>delete()</code>, <code>assign()</code>, <code>remove()</code></td></tr>
                <tr><td><code>backend.scheduler</code></td><td><code>ISchedulerAdapter</code></td><td><code>list()</code> &mdash; read-only job inspector</td></tr>
            </tbody>
        </table>

        <p>Two concrete implementations — swap in <code>main.py</code>, zero view changes:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python"># In-process (default):
backend = ServiceBackendAdapter(factory, user_service, scheduler)

# HTTP (local or remote):
backend = HttpBackendAdapter(base_url="http://localhost:8080")</code></pre>
        </div>

        <p><strong><code>/v1/</code> is the universal contract</strong> between the adapter layer and HTTP:</p>

        <ul>
            <li><code>HttpBackendAdapter</code> calls exactly these URLs (e.g. <code>POST /v1/auth/login</code>). It doesn&rsquo;t know whether it&rsquo;s talking to a local dev server or a remote host &mdash; it just calls <code>/v1/&hellip;</code> and trusts the contract.</li>
            <li><code>ServiceBackendAdapter</code> bypasses HTTP and calls Python methods directly &mdash; but the result is identical because both implement <code>IBackendAdapter</code>.</li>
            <li>Any external client (JS dashboard, mobile app, CLI) can call the same <code>/v1/</code> URLs. Write the endpoint once, consume from anywhere.</li>
            <li>Side-by-side versioning: add <code>/v2/</code> alongside <code>/v1/</code> during a migration. Old clients keep working. No flag day.</li>
            <li><strong>The swap is transparent to views</strong> because views call <code>backend.auth.login()</code>, never a URL. The URL is an implementation detail of <code>HttpBackendAdapter</code> only.</li>
        </ul>
```

- [ ] **Step 2: Verify the file renders by opening it (or run tests)**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add docs/api-docs/architecture.html
git commit -m "docs: expand Backend Adapter section in architecture.html — IBackendAdapter domain properties + /v1 contract"
```

---

## Task 7: Update `docs/api-docs/api-development.html` — live docs banner + endpoints table

**Files:**
- Modify: `docs/api-docs/api-development.html`

- [ ] **Step 1: Add live API reference banner after the intro paragraph**

Find:
```html
        <p>How to build HTTP endpoints in FlexTemplates &mdash; validation, error handling, testing,
        and the common CRUD patterns used throughout the codebase.</p>
```

Replace with:
```html
        <p>How to build HTTP endpoints in FlexTemplates &mdash; validation, error handling, testing,
        and the common CRUD patterns used throughout the codebase.</p>

        <blockquote>
            <p>&#128225; <strong>Live API Reference</strong> &rarr;
            <code>http://localhost:8080/docs</code> (Swagger UI) or
            <code>/redoc</code> (ReDoc) &mdash; run the app first. The live docs
            are the canonical reference for request/response schemas.</p>
        </blockquote>
```

- [ ] **Step 2: Add new endpoints table after the live docs banner (before "Quick Example")**

Find:
```html
        <p><strong>Prerequisites:</strong> Read <a href="template.html">CONTRACTS_GUIDE.md</a> first.
```

Replace with:
```html
        <h2>Available Endpoints</h2>

        <table>
            <thead>
                <tr><th>Endpoint</th><th>Method</th><th>Auth</th><th>Purpose</th></tr>
            </thead>
            <tbody>
                <tr><td><code>/v1/auth/login</code></td><td>POST</td><td>None</td><td>OAuth2 password flow, returns JWT</td></tr>
                <tr><td><code>/v1/auth/me</code></td><td>GET</td><td>Bearer</td><td>Current user&rsquo;s full profile</td></tr>
                <tr><td><code>/v1/users/</code></td><td>GET / POST / DELETE</td><td>Optional</td><td>User CRUD</td></tr>
                <tr><td><code>/v1/roles/</code></td><td>GET / POST / DELETE</td><td>Optional</td><td>Role CRUD</td></tr>
                <tr><td><code>/v1/roles/assign</code></td><td>POST</td><td>Optional</td><td>Assign role to user</td></tr>
                <tr><td><code>/v1/roles/remove</code></td><td>DELETE</td><td>Optional</td><td>Remove role from user</td></tr>
                <tr><td><code>/v1/caches/</code></td><td>GET / POST</td><td>Optional</td><td>Cache operations</td></tr>
                <tr><td><code>/v1/scheduler/jobs</code></td><td>GET</td><td>Optional</td><td>List scheduled jobs</td></tr>
            </tbody>
        </table>

        <p>See <code>http://localhost:8080/docs</code> for full request/response schemas.</p>

        <hr>

        <p><strong>Prerequisites:</strong> Read <a href="template.html">CONTRACTS_GUIDE.md</a> first.
```

- [ ] **Step 3: Fix stale router prefix in Quick Example code block**

Find (first occurrence in the file — inside the Quick Example):
```html
router = APIRouter(prefix="/roles", tags=["roles"])
```
with surrounding context:
```html
from lib.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


def get_service() -&gt; RoleService:
```

Replace with:
```html
from lib.services.role_service import RoleService

router = APIRouter(prefix="/v1/roles", tags=["roles"])


def get_service() -&gt; RoleService:
```

- [ ] **Step 4: Fix stale router prefix in "Full CRUD" code block**

Find (second occurrence — inside "Full CRUD — immediate operations"):
```html
router = APIRouter(prefix="/roles", tags=["roles"])


def get_service() -&gt; RoleService:
    return RoleService(ConnectionRegistry.get())


@router.post("")
def create_role(data: dict, service: RoleService = Depends(get_service)):
```

Replace with:
```html
router = APIRouter(prefix="/v1/roles", tags=["roles"])


def get_service() -&gt; RoleService:
    return RoleService(ConnectionRegistry.get())


@router.post("")
def create_role(data: dict, service: RoleService = Depends(get_service)):
```

- [ ] **Step 5: Fix test client URLs in Quick Example test block**

Find:
```html
def test_create_role_returns_id_and_name(api_client):
    response = api_client.post("/roles", json={"name": "admin", "description": "Admin"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "admin"
    assert "id" in data
```

Replace with:
```html
def test_create_role_returns_id_and_name(api_client):
    response = api_client.post("/v1/roles", json={"name": "admin", "description": "Admin"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "admin"
    assert "id" in data
```

- [ ] **Step 6: Fix staged/approval test URLs**

Find:
```html
    stage_resp = api_client.post("/users/with-roles/stage", json={
```

Replace with:
```html
    stage_resp = api_client.post("/v1/users/with-roles/stage", json={
```

Find:
```html
    confirm_resp = api_client.post("/users/with-roles/confirm")
    assert confirm_resp.status_code == 200

    users_resp = api_client.get("/users")
    assert any(u["username"] == "charlie" for u in users_resp.json()["users"])
```

Replace with:
```html
    confirm_resp = api_client.post("/v1/users/with-roles/confirm")
    assert confirm_resp.status_code == 200

    users_resp = api_client.get("/v1/users")
    assert any(u["username"] == "charlie" for u in users_resp.json()["users"])
```

Find:
```html
    api_client.post("/users/with-roles/stage", json={
```

Replace with:
```html
    api_client.post("/v1/users/with-roles/stage", json={
```

Find:
```html
    cancel_resp = api_client.post("/users/with-roles/cancel")
    assert cancel_resp.status_code == 200

    users_resp = api_client.get("/users")
    assert not any(u["username"] == "dave" for u in users_resp.json()["users"])
```

Replace with:
```html
    cancel_resp = api_client.post("/v1/users/with-roles/cancel")
    assert cancel_resp.status_code == 200

    users_resp = api_client.get("/v1/users")
    assert not any(u["username"] == "dave" for u in users_resp.json()["users"])
```

Find:
```html
    request_resp = api_client.post("/users/bulk-delete/request", json={
```

Replace with:
```html
    request_resp = api_client.post("/v1/users/bulk-delete/request", json={
```

Find:
```html
    approve_resp = api_client.post("/users/bulk-delete/approve", json={})
```

Replace with:
```html
    approve_resp = api_client.post("/v1/users/bulk-delete/approve", json={})
```

- [ ] **Step 7: Verify tests pass**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add docs/api-docs/api-development.html
git commit -m "docs: add live /docs banner + /v1 endpoints table to api-development.html"
```

---

## Task 8: Create `docs/api-docs/http-mode.html`

**Files:**
- Create: `docs/api-docs/http-mode.html`

- [ ] **Step 1: Create the file**

Create `docs/api-docs/http-mode.html` with this complete content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTTP Mode — FlexTemplates Docs</title>
    <link rel="stylesheet" href="css/docs.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
</head>
<body>
    <header>
        <h1>HTTP Mode</h1>
        <p class="breadcrumb">Builder Guides &rsaquo; HTTP Mode</p>
    </header>
    <main>

        <p>How to switch the app from in-process service calls to HTTP in one line &mdash; and what
        that means for security, testing, and the <code>/v1/</code> contract.</p>

        <hr>

        <h2>The Swap</h2>

        <p>One line in <code>main.py</code> switches the entire app from in-process to HTTP:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python"># Before (ServiceBackendAdapter — in-process):
backend = ServiceBackendAdapter(
    factory=factory,
    user_service=UserService(factory),
    scheduler=scheduler,
)

# After (HttpBackendAdapter — over HTTP):
from lib.adapters.http_backend_adapter import HttpBackendAdapter
backend = HttpBackendAdapter(base_url="http://localhost:8080")</code></pre>
        </div>

        <p>Both satisfy <code>IBackendAdapter</code>. Views and services see no difference &mdash;
        they call <code>backend.auth.login()</code>, never a URL.</p>

        <hr>

        <h2>Security Rules</h2>

        <ul>
            <li><strong>HTTPS required for any non-localhost URL.</strong>
            <code>HttpBackendAdapter</code> raises <code>ValueError</code> at construction time
            if you pass an <code>http://</code> URL whose hostname is not <code>localhost</code>,
            <code>127.0.0.1</code>, <code>::1</code>, or <code>0.0.0.0</code>.</li>
            <li><strong>JWT stored in RAM only.</strong> The token lives in
            <code>_HttpSession._token</code> &mdash; never logged, never written to disk.</li>
            <li><strong>Token cleared on logout and garbage collection.</strong>
            <code>logout()</code> calls <code>clear_credentials()</code>; no persistent
            state remains after the adapter object is collected.</li>
        </ul>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python"># These are fine (HTTP allowed for local addresses):
HttpBackendAdapter(base_url="http://localhost:8080")
HttpBackendAdapter(base_url="http://127.0.0.1:8080")

# This raises ValueError at construction:
HttpBackendAdapter(base_url="http://myapi.example.com")
# Use HTTPS for production:
HttpBackendAdapter(base_url="https://myapi.example.com")</code></pre>
        </div>

        <hr>

        <h2>Testing Pattern</h2>

        <p>Use the <code>_client=</code> escape hatch to inject a <code>TestClient</code>.
        This bypasses URL validation &mdash; no real network needed:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-python">from fastapi.testclient import TestClient
from lib.adapters.http_backend_adapter import HttpBackendAdapter

backend = HttpBackendAdapter(base_url="http://testserver", _client=TestClient(app))</code></pre>
        </div>

        <p>Pass <code>backend</code> as a prop to views, or call adapter methods directly in tests.
        The <code>_client=</code> parameter is the only way to use <code>HttpBackendAdapter</code>
        in tests without a running server.</p>

        <hr>

        <h2>Why <code>/v1/</code> Is the Contract</h2>

        <p>The <code>/v1/</code> prefix is the glue between the adapter layer and the HTTP layer:</p>

        <div style="position: relative;">
            <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
            <pre><code class="language-text">View code                    Always calls:  backend.auth.login()
                                                    &darr;
ServiceBackendAdapter        Calls:         UserService.authenticate()  (Python, no HTTP)
HttpBackendAdapter           Calls:         POST /v1/auth/login          (HTTP)
                                                    &darr;
FastAPI route                Handles:       POST /v1/auth/login
                             Calls:         UserService.authenticate()</code></pre>
        </div>

        <ul>
            <li><strong>The view never touches a URL.</strong> The URL lives inside
            <code>HttpBackendAdapter</code> only. Swapping the adapter does not require
            editing any view code.</li>
            <li><strong><code>/v1/</code> is a stability promise to every external consumer</strong>
            (JS dashboard, mobile app, CLI tool). Once published, it does not change without
            a version bump.</li>
            <li><strong>Any external client can use the same URLs.</strong> The Python app,
            a JS frontend, and a CLI tool all call <code>POST /v1/auth/login</code> and get
            the same contract. Write the endpoint once, consume from anywhere.</li>
            <li><strong>Side-by-side versioning.</strong> Add <code>/v2/auth/login</code>
            alongside <code>/v1/auth/login</code> during a migration &mdash; old clients keep
            working, new clients adopt the new version. No flag day, no breaking change.</li>
            <li><strong><code>ServiceBackendAdapter</code> skips the HTTP hop entirely</strong>
            but produces identical results &mdash; same service, same data, same
            <code>IBackendAdapter</code> interface.</li>
        </ul>

        <hr>

        <h2>When to Use Each Mode</h2>

        <table>
            <thead>
                <tr>
                    <th>Mode</th>
                    <th>Use when</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><code>ServiceBackendAdapter</code></td>
                    <td>Local Flet app, single process, direct DB access</td>
                </tr>
                <tr>
                    <td><code>HttpBackendAdapter</code></td>
                    <td>Remote backend, JS/mobile client, multi-process, microservice</td>
                </tr>
            </tbody>
        </table>

    </main>

    <nav class="page-nav">
        <div class="nav-group">
            <button class="btn-secondary" onclick="window.location.href='index.html'">&larr; Back to Hub</button>
            <button class="btn-secondary" onclick="window.location.href='view-development.html'">&larr; View Development</button>
        </div>
        <span class="progress">Builder Guides &middot; 4 of 4</span>
        <div class="nav-group">
            <button class="btn-primary" onclick="window.location.href='decision-trees.html'">Decision Trees &rarr;</button>
        </div>
    </nav>

    <script src="js/script.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify tests pass**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add docs/api-docs/http-mode.html
git commit -m "docs: create http-mode.html — HttpBackendAdapter swap, HTTPS rules, /v1 contract"
```

---

## Task 9: Update `docs/api-docs/index.html` — add HTTP Mode card + update API card description

**Files:**
- Modify: `docs/api-docs/index.html`

- [ ] **Step 1: Add HTTP Mode card to Builder Guides section**

Find:
```html
                    <a href="decision-trees.html" class="card">
                        <h3>&#127795; Decision Trees</h3>
                        <p>Five YES/NO decision trees: SimpleService vs StagingService, immediate vs staged vs approval, when to emit events.</p>
                        <button class="btn-primary">Choose Patterns &#8594;</button>
                    </a>
                </div>
            </section>
```

Replace with:
```html
                    <a href="decision-trees.html" class="card">
                        <h3>&#127795; Decision Trees</h3>
                        <p>Five YES/NO decision trees: SimpleService vs StagingService, immediate vs staged vs approval, when to emit events.</p>
                        <button class="btn-primary">Choose Patterns &#8594;</button>
                    </a>
                    <a href="http-mode.html" class="card">
                        <h3>&#128268; HTTP Mode</h3>
                        <p>Switch from in-process to HTTP with one line. Covers HTTPS enforcement, JWT handling, and the TestClient test pattern.</p>
                        <button class="btn-primary">Switch Modes &#8594;</button>
                    </a>
                </div>
            </section>
```

- [ ] **Step 2: Update API Development card description**

Find:
```html
                    <a href="api-development.html" class="card">
                        <h3>&#128268; API Development</h3>
                        <p>Request validation, HTTP error codes, response shaping, and testing endpoints. The canonical FastAPI route shape.</p>
                        <button class="btn-primary">Build Endpoints &#8594;</button>
                    </a>
```

Replace with:
```html
                    <a href="api-development.html" class="card">
                        <h3>&#128268; API Development</h3>
                        <p>Building routes, the three endpoint types, auth dependency, and error handling. Live API reference at <code>/docs</code>.</p>
                        <button class="btn-primary">Build Endpoints &#8594;</button>
                    </a>
```

- [ ] **Step 3: Verify tests pass**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add docs/api-docs/index.html
git commit -m "docs: add HTTP Mode card to index.html, update API card description"
```

---

## Task 10: Update `docs/api-docs/view-development.html` — section 5.5 domain sub-adapters

**Files:**
- Modify: `docs/api-docs/view-development.html`

- [ ] **Step 1: Replace the section 5.5 code example (flat methods → domain sub-adapters)**

Find this exact code block in section 5.5:
```html
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
```

Replace with:
```html
            <pre><code class="language-python">class ManageUsersView(ProtectedView):
    def __init__(self, page, props):
        super().__init__(page, props)
        self._backend = props.get("backend")   # IBackendAdapter — Service or Http

    def build_content(self):
        # Paginated user list
        result = self._backend.users.list(page=1, page_size=20)
        # → {"items": [...], "total": N, "page": 1, "page_size": 20, "pages": N}

        # Create / delete
        self._backend.users.create({"username": "alice", "email": "alice@x.com", "password": "..."})
        self._backend.users.delete(user_id_str)   # str UUID

        # Roles
        self._backend.roles.list()              # → [{"id": "...", "name": "admin"}]
        self._backend.roles.create("editor")
        self._backend.roles.delete(role_id_str)

        # Scheduler jobs (read-only)
        jobs = self._backend.scheduler.list()
        # → [{"id": "...", "func_name": "...", "trigger": "...", "next_run_time": ...}]</code></pre>
```

- [ ] **Step 2: Update the description paragraph below the code block**

Find:
```html
        <p><code>IBackendAdapter</code> is defined in
        <code>lib/adapters/backend_adapter.py</code>. To add a new backend operation,
        add it to the ABC and implement it in <code>ServiceBackendAdapter</code> &mdash;
        view code is unchanged.</p>
```

Replace with:
```html
        <p><code>IBackendAdapter</code> is defined in
        <code>lib/adapters/backend_adapter.py</code>. It is satisfied by both
        <code>ServiceBackendAdapter</code> (in-process) and <code>HttpBackendAdapter</code>
        (over HTTP). View code is unchanged regardless of which is wired in
        <code>main.py</code>. See <a href="http-mode.html">HTTP Mode</a> for the swap pattern.</p>
```

- [ ] **Step 3: Update section 2.4 ProtectedView description**

Find:
```html
        <p><code>ProtectedView.render()</code> checks <code>backend.current_user()</code>
        before calling <code>super().render()</code>. If <code>current_user()</code>
        returns <code>None</code>, it redirects to <code>/login</code> and returns an
        empty view.</p>
```

Replace with:
```html
        <p><code>ProtectedView.render()</code> checks <code>backend.auth.current_user()</code>
        before calling <code>super().render()</code>. If <code>current_user()</code>
        returns <code>None</code>, it redirects to <code>/login</code> and returns an
        empty view.</p>
```

- [ ] **Step 4: Verify tests pass**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add docs/api-docs/view-development.html
git commit -m "docs: update view-development.html section 5.5 to domain sub-adapter API"
```

---

## Task 11: Fix stale URL headings in `docs/api-docs/decision-trees.html`

**Files:**
- Modify: `docs/api-docs/decision-trees.html`

- [ ] **Step 1: Fix staged example heading**

Find:
```html
        <h3>Example &mdash; Staged: POST /users/with-roles/stage + confirm + cancel</h3>
```

Replace with:
```html
        <h3>Example &mdash; Staged: POST /v1/users/with-roles/stage + confirm + cancel</h3>
```

- [ ] **Step 2: Fix approval example heading**

Find:
```html
        <h3>Example &mdash; Approval: POST /users/bulk-delete/request + approve</h3>
```

Replace with:
```html
        <h3>Example &mdash; Approval: POST /v1/users/bulk-delete/request + approve</h3>
```

- [ ] **Step 3: Verify tests pass**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add docs/api-docs/decision-trees.html
git commit -m "docs: fix stale URL headings in decision-trees.html (/users → /v1/users)"
```

---

## Task 12: Add HTTPS ValueError entry to `docs/api-docs/troubleshooting.html`

**Files:**
- Modify: `docs/api-docs/troubleshooting.html`

- [ ] **Step 1: Locate the correct insertion point**

Read `docs/api-docs/troubleshooting.html` to find the `<ol>` category list at the top and the last `<details>` section. The new entry goes in a new `<details>` section at the end, or appended to the most relevant existing section. Look for `<details open id="vault-configuration-errors">` — this is the right place because the HTTPS error is a configuration/setup error.

- [ ] **Step 2: Add the HTTPS ValueError entry**

Find the closing tag of the "Vault & Configuration Errors" details block. It will look like:
```html
        </details>

        <hr>

        <details open id="flet-ui-errors">
```

Insert before the `<hr>` and the next `<details>`:
```html

            <h3>&ldquo;ValueError: HTTPS required for non-localhost URL&rdquo;</h3>

            <p><strong>What it means:</strong> <code>HttpBackendAdapter</code> was constructed with an <code>http://</code> URL pointing to a non-local host.</p>

            <p><strong>Why it happens:</strong> The adapter enforces HTTPS for any URL whose hostname is not <code>localhost</code>, <code>127.0.0.1</code>, <code>::1</code>, or <code>0.0.0.0</code>.</p>

            <p><strong>How to fix:</strong></p>
            <div style="position: relative;">
                <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
                <pre><code class="language-python"># WRONG — raises ValueError
backend = HttpBackendAdapter(base_url="http://myapi.example.com")

# CORRECT — use HTTPS for non-local URLs
backend = HttpBackendAdapter(base_url="https://myapi.example.com")

# OK — HTTP is allowed for local addresses
backend = HttpBackendAdapter(base_url="http://localhost:8080")</code></pre>
            </div>

            <p><strong>How to prevent:</strong> Always use <code>https://</code> in production configuration. Keep <code>http://localhost</code> for local development only.</p>

```

Note: you need to read the full troubleshooting.html to find the exact vault-configuration-errors closing tag. The insertion point is inside the `<details id="vault-configuration-errors">` block, just before its closing `</details>`.

- [ ] **Step 3: Add the new category to the `<ol>` navigation list at the top**

Find the jump-to navigation list. It currently ends with something like `<li><a href="#how-to-debug">How to Debug</a></li>`. Find the `<li><a href="#vault-configuration-errors">Vault &amp; Configuration Errors</a></li>` entry and verify the new entry belongs there (it's already in that section, so the `<ol>` doesn't need a new entry).

- [ ] **Step 4: Verify tests pass**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add docs/api-docs/troubleshooting.html
git commit -m "docs: add HTTPS ValueError entry to troubleshooting.html"
```

---

## Task 13: Add IBackendAdapter anti-pattern to `docs/api-docs/anti-patterns.html`

**Files:**
- Modify: `docs/api-docs/anti-patterns.html`

- [ ] **Step 1: Locate the container/wiring anti-patterns section**

Read `docs/api-docs/anti-patterns.html` to find the `<details id="container-wiring-anti-patterns">` section. The new entry will be appended as the last item in this section (or in the view anti-patterns section — whichever fits better based on the existing structure).

- [ ] **Step 2: Add the new anti-pattern entry**

Find the closing `</details>` of the last anti-pattern section (likely `container-wiring-anti-patterns`). The section ends with some `<h3>` block followed by `</details>`. Insert the following before the closing `</details>` of that section:

```html

            <h3>Anti-Pattern: Hardcoding <code>ServiceBackendAdapter</code> type in views or services</h3>

            <p><strong>The Problem</strong></p>

            <p>Importing a concrete adapter class directly in a view or service burns in the dependency and makes it impossible to swap to <code>HttpBackendAdapter</code>:</p>

            <div style="position: relative;">
                <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
                <pre><code class="language-python"># WRONG — hardcoded concrete type in a view
from lib.adapters.backend_adapter import ServiceBackendAdapter

class ManageUsersView(ProtectedView):
    def build_content(self):
        backend = ServiceBackendAdapter(factory, user_service, scheduler)
        result = backend.users.list(page=1)</code></pre>
            </div>

            <p><strong>Why it breaks:</strong></p>
            <ul>
                <li>Switching to HTTP mode requires editing every view that hardcodes the type.</li>
                <li>Tests cannot inject a mock adapter &mdash; the view builds its own.</li>
                <li>Defeats the entire point of <code>IBackendAdapter</code>.</li>
            </ul>

            <p><strong>The fix:</strong> Always receive <code>IBackendAdapter</code> via <code>props["backend"]</code>. The concrete type is wired in <code>main.py</code> only.</p>

            <div style="position: relative;">
                <button class="copy-button" onclick="copyToClipboard(this)">Copy</button>
                <pre><code class="language-python"># CORRECT — type comes from props; main.py decides which concrete class
class ManageUsersView(ProtectedView):
    def __init__(self, page, props):
        super().__init__(page, props)
        self._backend = props.get("backend")   # IBackendAdapter — Service or Http

    def build_content(self):
        result = self._backend.users.list(page=1)</code></pre>
            </div>

```

- [ ] **Step 3: Verify tests pass**

```bash
pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add docs/api-docs/anti-patterns.html
git commit -m "docs: add IBackendAdapter concrete-type anti-pattern to anti-patterns.html"
```

---

## Task 14: Final verification commit

- [ ] **Step 1: Run the full test suite one final time**

```bash
pytest tests/ -q
```

Expected: all tests pass (518+). Zero Python code was changed — this confirms no doc edits accidentally broke anything.

- [ ] **Step 2: Verify new HTML page opens in browser**

Open `docs/api-docs/http-mode.html` in a browser. Confirm:
- All 5 sections render (The Swap, Security Rules, Testing Pattern, Why /v1/, When to Use Each Mode)
- Code blocks have syntax highlighting
- Navigation buttons link to the correct pages
- No obvious formatting issues

- [ ] **Step 3: Verify index.html shows 4 Builder Guides cards**

Open `docs/api-docs/index.html` in a browser. Confirm the Builder Guides section now shows 4 cards: API Development, View Development, Decision Trees, HTTP Mode.

- [ ] **Step 4: Commit if any final tweaks were needed**

```bash
git add docs/api-docs/
git commit -m "docs: Phase 5D — update all docs for HttpBackendAdapter, /v1 versioning, new endpoints"
```

---

## Notes for the Implementer

**CONVENTIONS.md — find insertion point:** The file ends with a numbered section (e.g. `## 8. Action Signatures`). Append the new `/v1/` section as `## 9.` or as the next available number at the end of the file. Do not use a placeholder for the section number — read the file first to find the last section number.

**troubleshooting.html — find vault section:** Read the file to find `<details open id="vault-configuration-errors">`. The HTTPS error entry belongs inside this `<details>` block, before its `</details>` closing tag, because it's a configuration error (wrong URL scheme).

**anti-patterns.html — find insertion point:** Read the file to find the last `<details>` section. The IBackendAdapter anti-pattern belongs in the "Container & Wiring Anti-Patterns" section (`<details id="container-wiring-anti-patterns">`), before its closing `</details>`.

**template.html:** No changes needed — a thorough grep confirmed no stale route URLs or `ServiceBackendAdapter` references are present in this file.

**No Python code changes:** Every task in this plan is docs-only. If `pytest` fails after any task, you introduced an accidental Python change — use `git diff` to find it.
