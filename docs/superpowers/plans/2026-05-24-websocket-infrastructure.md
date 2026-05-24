# WebSocket Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable, domain-agnostic WebSocket layer so browser clients can connect to named rooms with JWT authentication and receive real-time broadcasts — the foundation for any future online feature.

**Architecture:** A `ConnectionManager` tracks `WebSocket` objects by room ID and handles broadcast/prune. A FastAPI route validates a JWT from the `?token` query param (browsers can't send `Authorization` headers during the WS handshake), joins the client to the requested room, and relays all inbound messages back to the room. `router_registry` detects a `ws_router` attribute on route modules and mounts it directly on the `app` at `/ws` — bypassing the `/v1` auth middleware entirely.

**Tech Stack:** FastAPI built-in WebSocket support, `python-jose` (already in project) for JWT validation, FastAPI `TestClient` for synchronous WebSocket tests.

---

## File Map

| File | Action | What it does |
|---|---|---|
| `lib/api/websocket/__init__.py` | Create | empty package marker |
| `lib/api/websocket/manager.py` | Create | `ConnectionManager` — rooms, connect, disconnect, broadcast, prune |
| `lib/api/routes/ws.py` | Create | WebSocket endpoint — JWT auth, lifecycle events, relay loop |
| `lib/api/router_registry.py` | Modify | detect `ws_router` on route modules; mount at `/ws` directly on `app` |
| `main.py` | Modify | instantiate `ConnectionManager`; call `ws_route.set_manager()` after `mount_routes()` |
| `tests/test_websocket.py` | Create | 5 unit tests (manager) + 6 integration tests (endpoint) |
| `tests/test_smoke.py` | Modify | add `lib.api.websocket.manager` and `lib.api.routes.ws` |

---

## Task 1: ConnectionManager

**Files:**
- Create: `lib/api/websocket/__init__.py`
- Create: `lib/api/websocket/manager.py`
- Create: `tests/test_websocket.py` (first 5 unit tests)

- [ ] **Step 1: Write the failing unit tests**

Create `tests/test_websocket.py`:

```python
"""Tests for ConnectionManager and the /ws WebSocket endpoint."""
import asyncio
import pytest


# ── ConnectionManager unit tests (mock WebSocket, no HTTP server needed) ─────

class _MockWs:
    """Minimal WebSocket stand-in that records what was sent."""
    def __init__(self):
        self.sent: list[dict] = []

    async def accept(self) -> None:
        pass

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


class _DeadWs:
    """Stand-in that explodes on send — simulates a dropped connection."""
    async def accept(self) -> None:
        pass

    async def send_json(self, _: dict) -> None:
        raise RuntimeError("connection lost")


@pytest.fixture
def manager():
    from lib.api.websocket.manager import ConnectionManager
    return ConnectionManager()


def test_manager_connect_adds_to_room(manager):
    ws = _MockWs()
    asyncio.run(manager.connect("room1", ws))
    assert manager.room_size("room1") == 1
    assert "room1" in manager.rooms()


def test_manager_disconnect_removes_from_room(manager):
    ws = _MockWs()
    asyncio.run(manager.connect("room1", ws))
    manager.disconnect("room1", ws)
    assert manager.room_size("room1") == 0
    assert "room1" not in manager.rooms()


def test_manager_broadcast_sends_to_all_in_room(manager):
    ws_a, ws_b = _MockWs(), _MockWs()
    asyncio.run(manager.connect("room1", ws_a))
    asyncio.run(manager.connect("room1", ws_b))
    asyncio.run(manager.broadcast("room1", {"type": "ping", "payload": {}}))
    assert ws_a.sent == [{"type": "ping", "payload": {}}]
    assert ws_b.sent == [{"type": "ping", "payload": {}}]


def test_manager_broadcast_prunes_dead_connections(manager):
    dead = _DeadWs()
    asyncio.run(manager.connect("room1", dead))
    asyncio.run(manager.broadcast("room1", {"type": "ping", "payload": {}}))
    assert manager.room_size("room1") == 0


def test_manager_broadcast_all_reaches_every_room(manager):
    ws_a, ws_b = _MockWs(), _MockWs()
    asyncio.run(manager.connect("room-a", ws_a))
    asyncio.run(manager.connect("room-b", ws_b))
    asyncio.run(manager.broadcast_all({"type": "server.notice", "payload": {}}))
    assert ws_a.sent == [{"type": "server.notice", "payload": {}}]
    assert ws_b.sent == [{"type": "server.notice", "payload": {}}]
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_websocket.py -v
```

Expected: `ModuleNotFoundError: No module named 'lib.api.websocket'`

- [ ] **Step 3: Create the package marker**

Create `lib/api/websocket/__init__.py` — empty file.

- [ ] **Step 4: Implement `ConnectionManager`**

Create `lib/api/websocket/manager.py`:

```python
"""Domain-agnostic WebSocket room manager.

Owns no application logic — tracks connections by room ID and broadcasts JSON.
Dead connections are pruned lazily on the next broadcast; no background thread needed.
All public async methods are called from the Uvicorn event loop thread.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, room_id: str, ws: WebSocket) -> None:
        """Accept the WebSocket upgrade and register the connection in room_id."""
        await ws.accept()
        self._rooms[room_id].add(ws)

    def disconnect(self, room_id: str, ws: WebSocket) -> None:
        """Remove the connection. Prunes the room entry when it becomes empty."""
        self._rooms[room_id].discard(ws)
        if not self._rooms[room_id]:
            self._rooms.pop(room_id, None)

    async def broadcast(self, room_id: str, message: dict) -> None:
        """Send message to every live connection in room_id.
        Connections that raise on send are removed silently."""
        dead: set[WebSocket] = set()
        for ws in list(self._rooms.get(room_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._rooms[room_id].discard(ws)

    async def broadcast_all(self, message: dict) -> None:
        """Send message to every client in every room."""
        for room_id in list(self._rooms):
            await self.broadcast(room_id, message)

    def rooms(self) -> list[str]:
        """Return the list of currently active room IDs."""
        return list(self._rooms)

    def room_size(self, room_id: str) -> int:
        """Return the number of active connections in room_id."""
        return len(self._rooms.get(room_id, set()))
```

- [ ] **Step 5: Run tests to confirm they pass**

```
pytest tests/test_websocket.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```
git add lib/api/websocket/__init__.py lib/api/websocket/manager.py tests/test_websocket.py
git commit -m "feat: add ConnectionManager — room-based WebSocket broadcast"
```

---

## Task 2: WebSocket Route + Integration Tests

**Files:**
- Create: `lib/api/routes/ws.py`
- Modify: `tests/test_websocket.py` (append 6 integration tests)

- [ ] **Step 1: Append the 6 integration tests to `tests/test_websocket.py`**

Add the following to the bottom of `tests/test_websocket.py`:

```python
# ── WebSocket endpoint integration tests ──────────────────────────────────────
#
# All tests use FastAPI's synchronous TestClient — no pytest-asyncio needed.
# Each test gets a fresh ConnectionManager via the ws_app fixture so state
# never leaks between tests.

@pytest.fixture
def ws_app():
    """Minimal FastAPI app with only the ws_router mounted — fast, isolated."""
    from fastapi import FastAPI
    from lib.api.websocket.manager import ConnectionManager
    import lib.api.routes.ws as ws_module

    manager = ConnectionManager()
    ws_module.set_manager(manager)

    app = FastAPI()
    app.include_router(ws_module.ws_router, prefix="/ws")
    return app


def test_ws_rejects_missing_token(ws_app):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    client = TestClient(ws_app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/room1") as ws:
            ws.receive_json()
    assert exc_info.value.code == 4001


def test_ws_rejects_invalid_token(ws_app):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    client = TestClient(ws_app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/room1?token=not.a.valid.jwt") as ws:
            ws.receive_json()
    assert exc_info.value.code == 4001


def test_ws_connect_joins_room(ws_app):
    from fastapi.testclient import TestClient
    from lib.auth.jwt_handler import create_token

    client = TestClient(ws_app)
    token = create_token({"sub": "user-123", "roles": ["player"]})

    with client.websocket_connect(f"/ws/lobby?token={token}") as ws:
        msg = ws.receive_json()

    assert msg["type"] == "room.joined"
    assert msg["payload"]["user"]["id"] == "user-123"
    assert msg["payload"]["user"]["roles"] == ["player"]


def test_ws_broadcast_reaches_all_clients(ws_app):
    from fastapi.testclient import TestClient
    from lib.auth.jwt_handler import create_token

    client = TestClient(ws_app)
    token_a = create_token({"sub": "user-a", "roles": []})
    token_b = create_token({"sub": "user-b", "roles": []})

    with client.websocket_connect(f"/ws/room1?token={token_a}") as ws_a:
        ws_a.receive_json()  # ws_a's own room.joined
        with client.websocket_connect(f"/ws/room1?token={token_b}") as ws_b:
            ws_a.receive_json()  # ws_b's room.joined broadcast to room (ws_a receives)
            ws_b.receive_json()  # ws_b's own room.joined

            ws_a.send_json({"type": "ping", "payload": {}})

            msg_a = ws_a.receive_json()
            msg_b = ws_b.receive_json()

    assert msg_a["type"] == "ping"
    assert msg_b["type"] == "ping"
    assert msg_a["payload"]["from"] == "user-a"
    assert msg_b["payload"]["from"] == "user-a"


def test_ws_disconnect_broadcasts_room_left(ws_app):
    from fastapi.testclient import TestClient
    from lib.auth.jwt_handler import create_token

    client = TestClient(ws_app)
    token_a = create_token({"sub": "user-a", "roles": []})
    token_b = create_token({"sub": "user-b", "roles": []})

    with client.websocket_connect(f"/ws/room1?token={token_a}") as ws_a:
        ws_a.receive_json()  # ws_a's room.joined

        with client.websocket_connect(f"/ws/room1?token={token_b}") as ws_b:
            ws_a.receive_json()  # ws_b's room.joined (broadcast; ws_a receives)
            ws_b.receive_json()  # ws_b's own room.joined
        # ws_b context exited — connection closed

        msg = ws_a.receive_json()  # ws_a receives the room.left broadcast

    assert msg["type"] == "room.left"
    assert msg["payload"]["user"]["id"] == "user-b"


def test_ws_clients_in_different_rooms_isolated(ws_app):
    from fastapi.testclient import TestClient
    from lib.auth.jwt_handler import create_token

    client = TestClient(ws_app)
    token_a = create_token({"sub": "user-a", "roles": []})
    token_b = create_token({"sub": "user-b", "roles": []})

    with client.websocket_connect(f"/ws/room-a?token={token_a}") as ws_a:
        ws_a.receive_json()  # ws_a's room.joined in room-a
        with client.websocket_connect(f"/ws/room-b?token={token_b}") as ws_b:
            ws_b.receive_json()  # ws_b's room.joined in room-b
            # ws_b joining room-b does NOT broadcast to room-a, so ws_a has nothing new

            ws_a.send_json({"type": "room-a-only", "payload": {}})
            ws_b.send_json({"type": "room-b-only", "payload": {}})

            msg_a = ws_a.receive_json()
            msg_b = ws_b.receive_json()

    # Each client receives only from their own room
    assert msg_a["type"] == "room-a-only"
    assert msg_b["type"] == "room-b-only"
```

- [ ] **Step 2: Run new tests to confirm they fail**

```
pytest tests/test_websocket.py::test_ws_rejects_missing_token -v
```

Expected: `ModuleNotFoundError: No module named 'lib.api.routes.ws'` or `ImportError`.

- [ ] **Step 3: Implement `lib/api/routes/ws.py`**

Create `lib/api/routes/ws.py`:

```python
"""WebSocket endpoint — JWT auth + room lifecycle + generic relay.

Authentication: JWT is passed as ?token=<JWT> query param because browsers
cannot send Authorization headers during the WebSocket upgrade handshake.
Invalid or missing tokens are rejected with close code 4001 before the
connection is accepted into any room.

Message contract: all messages (both directions) use the Event shape:
    {"type": "domain.event", "payload": {...}}

The relay loop re-broadcasts every inbound client message to the whole room,
injecting "from": user_id into the payload. Application routes that need
custom dispatch (e.g. a game engine) replace or wrap this loop.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket
from starlette.websockets import WebSocketDisconnect

from lib.api.websocket.manager import ConnectionManager
from lib.auth.jwt_handler import JWTError, decode_token

_manager: ConnectionManager | None = None


def set_manager(m: ConnectionManager) -> None:
    """Called once at startup from main.py — injects the shared ConnectionManager."""
    global _manager
    _manager = m


ws_router = APIRouter()


@ws_router.websocket("/{room_id}")
async def ws_endpoint(
    room_id: str,
    ws: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    # 1. Authenticate — reject before accepting to avoid unnecessary resource use
    if not token:
        await ws.close(code=4001)
        return
    try:
        claims = decode_token(token)
    except JWTError:
        await ws.close(code=4001)
        return

    user = {"id": claims["sub"], "roles": claims.get("roles", [])}

    # 2. Join room — accept() happens inside manager.connect()
    await _manager.connect(room_id, ws)
    await _manager.broadcast(room_id, {"type": "room.joined", "payload": {"user": user}})

    # 3. Relay loop — re-broadcasts every client message to the room with sender identity
    try:
        while True:
            data = await ws.receive_json()
            await _manager.broadcast(room_id, {
                "type": data.get("type", "message"),
                "payload": {**data.get("payload", {}), "from": user["id"]},
            })
    except WebSocketDisconnect:
        _manager.disconnect(room_id, ws)
        await _manager.broadcast(room_id, {"type": "room.left", "payload": {"user": user}})
```

- [ ] **Step 4: Run all WebSocket tests**

```
pytest tests/test_websocket.py -v
```

Expected: 11 passed (5 unit + 6 integration).

- [ ] **Step 5: Run full suite to confirm no regressions**

```
pytest --tb=short -q
```

Expected: all existing tests still pass (only new tests added).

- [ ] **Step 6: Commit**

```
git add lib/api/routes/ws.py tests/test_websocket.py
git commit -m "feat: add WebSocket endpoint with JWT auth and room relay"
```

---

## Task 3: Router Registry + main.py + Smoke Test

**Files:**
- Modify: `lib/api/router_registry.py`
- Modify: `main.py`
- Modify: `tests/test_smoke.py`

- [ ] **Step 1: Add `ws_router` detection to `router_registry.py`**

Current file at `lib/api/router_registry.py`:

```python
def mount_routes(app: FastAPI, config, package: str = "lib.api.routes") -> None:
    from lib.api.v1 import make_v1_router
    v1_router, public, protected = make_v1_router(config)

    mod = importlib.import_module(package)
    for _, name, _ in pkgutil.iter_modules(mod.__path__):
        sub = importlib.import_module(f"{package}.{name}")
        if hasattr(sub, "public_router"):
            public.include_router(sub.public_router)
        if hasattr(sub, "router"):
            target = public if getattr(sub, "_PUBLIC_ROUTER", False) else protected
            target.include_router(sub.router)

    v1_router.include_router(public)
    v1_router.include_router(protected)
    app.include_router(v1_router)
```

Replace with (add 2 lines: the `ws_router` check inside the loop and update the module docstring):

```python
"""
mount_routes — auto-discover and mount every router in lib/api/routes/.

Each route module is mounted through the v1 contract router:
  - Modules with _PUBLIC_ROUTER = True → public sub-router (rate limited, no auth)
  - All other modules → protected sub-router (rate limited + Bearer JWT)
  - Modules with ws_router → mounted directly on app at /ws (no v1 middleware)

Drop a new file in routes/ that defines `router = APIRouter(...)` and it is
protected automatically — no manual registration, no forgotten auth.

For WebSocket routes: define `ws_router = APIRouter()` instead. It bypasses
all v1 middleware and handles its own JWT validation from the ?token query param.
"""
from __future__ import annotations

import importlib
import pkgutil
from fastapi import FastAPI


def mount_routes(app: FastAPI, config, package: str = "lib.api.routes") -> None:
    from lib.api.v1 import make_v1_router
    v1_router, public, protected = make_v1_router(config)

    mod = importlib.import_module(package)
    for _, name, _ in pkgutil.iter_modules(mod.__path__):
        sub = importlib.import_module(f"{package}.{name}")
        if hasattr(sub, "public_router"):
            public.include_router(sub.public_router)
        if hasattr(sub, "router"):
            target = public if getattr(sub, "_PUBLIC_ROUTER", False) else protected
            target.include_router(sub.router)
        if hasattr(sub, "ws_router"):
            app.include_router(sub.ws_router, prefix="/ws")

    v1_router.include_router(public)
    v1_router.include_router(protected)
    app.include_router(v1_router)
```

- [ ] **Step 2: Wire `ConnectionManager` into `main.py`**

In `main.py`, locate this block (around line 192–197):

```python
    mount_routes(api_app, config)
    from lib.api.routes import scheduler as scheduler_routes
    scheduler_routes.set_scheduler(scheduler)
    from lib.api.routes.auth import set_email_sender as _set_auth_email_sender
    _set_auth_email_sender(email_sender)
```

Replace with:

```python
    mount_routes(api_app, config)
    from lib.api.routes import scheduler as scheduler_routes
    scheduler_routes.set_scheduler(scheduler)
    from lib.api.routes.auth import set_email_sender as _set_auth_email_sender
    _set_auth_email_sender(email_sender)
    from lib.api.websocket.manager import ConnectionManager
    from lib.api.routes import ws as ws_route
    _ws_manager = ConnectionManager()
    ws_route.set_manager(_ws_manager)
```

- [ ] **Step 3: Expose `ws_manager` in Flet props**

In `main.py`, locate the `router.set_props_factory` call. Find the `"dev_nav": True` line at the end of the props dict and add `ws_manager` before it:

```python
    router.set_props_factory(lambda: {
        # ... existing keys unchanged ...
        "ws_manager":        _ws_manager,
        "dev_nav": True,
    })
```

- [ ] **Step 4: Add new modules to the smoke test**

In `tests/test_smoke.py`, in the `@pytest.mark.parametrize` list for `test_module_imports_cleanly`, add these two entries (anywhere in the list is fine):

```python
        "lib.api.websocket.manager",
        "lib.api.routes.ws",
```

- [ ] **Step 5: Run the full test suite**

```
pytest --tb=short -q
```

Expected: all tests pass (existing count + 11 new WebSocket tests + 2 new smoke entries).

- [ ] **Step 6: Commit**

```
git add lib/api/router_registry.py main.py tests/test_smoke.py
git commit -m "feat: wire WebSocket infrastructure into router registry and main.py"
```

---

## Extending This Layer (Reference)

**Adding a game-specific route** (`lib/api/routes/cah_ws.py`):

```python
from fastapi import APIRouter, Query, WebSocket
from starlette.websockets import WebSocketDisconnect
from lib.api.websocket.manager import ConnectionManager
from lib.auth.jwt_handler import JWTError, decode_token

_manager = None

def set_manager(m: ConnectionManager) -> None:
    global _manager
    _manager = m

ws_router = APIRouter()

@ws_router.websocket("/cah/{room_id}")
async def cah_ws(room_id: str, ws: WebSocket, token: str | None = Query(default=None)):
    if not token:
        await ws.close(code=4001); return
    try:
        claims = decode_token(token)
    except JWTError:
        await ws.close(code=4001); return

    user = {"id": claims["sub"], "roles": claims.get("roles", [])}
    await _manager.connect(room_id, ws)
    await _manager.broadcast(room_id, {"type": "room.joined", "payload": {"user": user}})

    try:
        while True:
            data = await ws.receive_json()
            match data.get("type"):
                case "card.submit":
                    # call your game service here, then broadcast new state
                    await _manager.broadcast(room_id, {"type": "game.state", "payload": {}})
                case _:
                    pass  # ignore unknown message types
    except WebSocketDisconnect:
        _manager.disconnect(room_id, ws)
        await _manager.broadcast(room_id, {"type": "room.left", "payload": {"user": user}})
```

This gets auto-discovered by `router_registry` and mounts at `/ws/cah/{room_id}` — no changes to the infrastructure needed.
