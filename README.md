# FlexTemplates 2.0

A LEGO-style Python framework combining **Flet** (UI), **FastAPI** (REST + WebSocket), and **SQLAlchemy** (ORM) in a single process. Every layer communicates through three Pydantic contracts — `ActionRequest`, `ActionResult`, `Event` — so any component is swappable without touching the rest.

**Use it as a starting point** for desktop apps, browser-served apps, real-time multiplayer games, dashboards, or any project that needs auth, a database, and a UI out of the box.

---

## Quick Start

```bash
pip install -e .
python main.py        # desktop window + API on localhost:8080
pytest tests/ -q      # 631 tests, ~80% coverage
```

---

## What's Included

| Feature | Location |
|---|---|
| Flet UI (desktop or web browser) | `lib/views/`, `lib/ui/` |
| FastAPI REST backend (auto-discovered routes) | `lib/api/routes/` |
| WebSocket rooms with JWT auth | `lib/api/routes/ws.py`, `lib/api/websocket/` |
| SQLAlchemy ORM + Alembic migrations | `lib/database/`, `lib/models/` |
| User & role management | `lib/services/user_service.py` |
| JWT auth (login, protected routes, WS handshake) | `lib/auth/` |
| Encrypted secrets vault (two-key design) | `lib/security/` |
| Email (console or SMTP, swappable) | `lib/services/email_service.py` |
| Unit of Work (preview → confirm flows) | `lib/database/uow.py` |
| EventBus (pub/sub, in-process) | `lib/core/events.py` |
| HTTP backend adapter (Flet → FastAPI) | `lib/adapters/http_backend_adapter.py` |
| AppConfig (env vars + `.secrets/.env`) | `lib/config/settings.py` |

---

## Architecture

```
main.py              ← only file that names concrete classes; wires everything
  │
  ├── lib/views/     ← Flet pages; receive services via props dict
  ├── lib/api/       ← FastAPI routes (REST) + WebSocket endpoint
  │
  ├── lib/services/  ← business logic (SimpleService / StagingService)
  ├── lib/repositories/ ← CRUD on ORM models
  ├── lib/models/    ← SQLAlchemy tables
  ├── lib/database/  ← SessionFactory, ConnectionRegistry, UnitOfWork
  │
  ├── lib/auth/      ← JWT encode/decode, login route
  ├── lib/security/  ← Vault (Fernet-encrypted secrets)
  ├── lib/config/    ← AppConfig (pydantic-settings)
  └── lib/core/      ← IService, SimpleService, StagingService, EventBus
```

**One rule:** `main.py` is the only file allowed to name concrete implementations. Everything else depends on interfaces.

---

## Three Contracts (The LEGO Plugs)

```python
# lib/contracts/base.py

ActionRequest(action="create_user", data={"username": "alice", "email": "..."})
ActionResult(success=True, data={"id": "abc", "username": "alice"})
Event(type="user.created", payload={"id": "abc"})
```

Services receive `ActionRequest`, return `ActionResult`. Events flow through `EventBus`. Nothing else crosses layers.

---

## Three API Endpoint Types

Every route is one of three patterns — pick before writing:

| Type | When | Example |
|---|---|---|
| **Immediate** | Simple CRUD, low risk | `GET /users`, `DELETE /users/{id}` |
| **Staged** | Multi-step, has side effects | `POST /users/with-roles/stage → /confirm` |
| **Approval-required** | Bulk ops, irreversible | `POST /users/bulk-delete/request → /approve` |

See `docs/reference/DECISION_TREES.md` for the full decision logic.

---

## WebSocket Rooms

Any route module that defines `ws_router` gets auto-mounted at `/ws`:

```python
# lib/api/routes/my_game.py
ws_router = APIRouter()

@ws_router.websocket("/{room_id}")
async def game_endpoint(room_id: str, ws: WebSocket, token: str = Query(...)):
    # JWT validated via ?token=<JWT> (browsers can't send Authorization headers on WS upgrade)
    claims = decode_token(token)
    await manager.connect(room_id, ws)
    ...
```

The `ConnectionManager` is domain-agnostic — it knows rooms, connections, and broadcast. Game logic lives in the route handler.

```python
# Any service or view can inspect room state via props["ws_manager"]
manager.room_size("lobby-1")   # → 3
manager.rooms()                # → ["lobby-1", "game-42"]
```

---

## Running as a Web App

Set `APP_VIEW=web` in `.secrets/.env` to serve the Flet UI to browsers instead of opening a desktop window:

```ini
# .secrets/.env
APP_VIEW=web
FLET_PORT=8550
```

Friends connect to `http://your-server:8550`. The FastAPI backend runs separately on `API_PORT` (default 8080).

---

## Key Files

| File | Read when |
|---|---|
| `main.py` | Understanding startup / changing DI wiring |
| `lib/contracts/base.py` | Writing any new service or route |
| `lib/core/interfaces.py` | Implementing a new service or repository |
| `lib/services/user_service.py` | Reference: immediate + staged operations |
| `lib/repositories/user_repository.py` | Reference: CRUD + relationship loading |
| `lib/api/routes/users.py` | Reference: all three endpoint types |
| `lib/api/websocket/manager.py` | Reference: WebSocket room management |
| `tests/conftest.py` | Test fixtures — in-memory SQLite, HTTP adapters |

---

## Adding a New Feature

### REST endpoint (30 seconds)
Drop a file in `lib/api/routes/` — it's auto-discovered. No registration needed.

```python
# lib/api/routes/products.py
router = APIRouter(prefix="/products", tags=["products"])

@router.get("/{id}")
def get_product(id: uuid.UUID):
    ...
```

### Flet view (30 seconds)
Drop a file in `lib/views/` — navigating to `/products` routes there automatically.

```python
# lib/views/products.py
def view(page: ft.Page, props: dict):
    service = props["product_service"]  # injected by router
    ...
    return ft.Column([...])
```

### WebSocket endpoint
Drop a file in `lib/api/routes/` with a `ws_router`:

```python
# lib/api/routes/game_ws.py
ws_router = APIRouter()

@ws_router.websocket("/{room_id}")
async def game_ws(room_id: str, ws: WebSocket, token: str = Query(...)):
    ...
```

### New entity (model → repo → service → route)
See `docs/examples/API_PATTERN_TEMPLATE.md` for the full step-by-step.

---

## Configuration

All config lives in `.secrets/.env` (never project-root `.env`):

```ini
# .secrets/.env

# API
API_HOST=0.0.0.0
API_PORT=8080

# UI
APP_VIEW=desktop          # desktop | web | headless
FLET_PORT=8550            # used when APP_VIEW=web

# Database (name derives from key: DATABASE_POSTGRES → registered as "postgres")
DATABASE_POSTGRES=postgresql://user:pass@localhost/myapp

# Auth
JWT_SECRET_KEY=your-secret-key

# Email
EMAIL_SENDER=smtp         # console | smtp
SMTP_HOST=smtp.example.com
SMTP_PASSWORD=secret

# Vault
VAULT_MASTER_KEY=...
VAULT_CONFIRM_KEY=...
```

---

## Testing

```bash
pytest tests/ -q                          # 631 tests
pytest tests/test_websocket.py -v         # WebSocket tests
pytest tests/test_api_routes.py -v        # API route tests
pytest tests/test_http_adapters.py -v     # HTTP adapter tests
pytest --cov=lib --cov-report=term-missing  # with coverage
```

Tests use in-memory SQLite — no external database needed. WebSocket tests use FastAPI's `TestClient` — no server needed.

---

## Documentation

| Folder | Read when |
|---|---|
| `docs/core/` | Before writing any code — ARCHITECTURE → CONVENTIONS → CONTRACTS_GUIDE |
| `docs/guides/` | Building a specific feature — API_DEVELOPMENT, VIEW_DEVELOPMENT |
| `docs/reference/` | Looking up a pattern — DECISION_TREES, VAULT_USAGE, TESTING |
| `docs/troubleshooting/` | Something broke — TROUBLESHOOTING, ANTI_PATTERNS |
| `docs/examples/` | Complete worked examples — API_PATTERN_TEMPLATE, PONG_EXAMPLE |
| `docs/api-docs/` | Interactive HTML docs portal (open `index.html` in browser) |

---

## Design Principles

1. **LEGO architecture** — each component has one job and clean interfaces; swap parts without touching the rest
2. **`main.py` is the only wiring file** — all concrete class names live there; everything else depends on interfaces
3. **Contracts, not direct calls** — services speak `ActionRequest`/`ActionResult`; WebSocket messages use `{"type": "...", "payload": {...}}`
4. **Auto-discovery** — drop a file in `lib/api/routes/` or `lib/views/` and it appears; no registration
5. **Testability first** — in-memory SQLite, no mocking required; all 631 tests run without external dependencies
6. **Secrets stay in `.secrets/.env`** — never the project root; `AppConfig` reads from there automatically

---

## License

Part of the FlexTemplates project.
