# WebSocket Infrastructure — Design Spec

## Goal

Add a reusable, domain-agnostic WebSocket layer to the framework so any future online feature
(multiplayer games, live dashboards, collaborative tools) can push real-time events to browser
clients over a persistent connection.

## Reusability Principles

This infrastructure knows nothing about games, players, cards, or any application domain.
It provides three primitives:

- **Rooms** — named channels; any string is a valid room ID
- **Broadcast** — send a JSON message to every client in a room
- **Relay** — forward client messages back to the room (with sender identity injected)

Application-level semantics (what "round.start" means, what "card.submit" does) live entirely
in the consuming route or service. Swapping from Cards Against Humanity to a live dashboard
means writing a new route — the `ConnectionManager` is unchanged.

## Architecture

```
Browser
  │  wss://host:8080/ws/{room_id}?token=<JWT>
  ▼
lib/api/routes/ws.py          ← WebSocket endpoint (auth + lifecycle + relay)
  │
  ├── lib/api/websocket/manager.py  ← ConnectionManager (rooms, broadcast, prune)
  │
  └── lib/auth/jwt_handler.py       ← decode_token() (reused from REST layer)
```

WebSocket routes live at `/ws/{room_id}` — parallel to `/v1`, not under it. This mirrors
the version boundary design: `/v1` may become `/v2` without touching the WebSocket layer,
and `/ws` may gain its own versioning independently.

## Files

| File | Action | Responsibility |
|---|---|---|
| `lib/api/websocket/__init__.py` | Create | empty |
| `lib/api/websocket/manager.py` | Create | `ConnectionManager` — rooms, connect, disconnect, broadcast |
| `lib/api/routes/ws.py` | Create | WebSocket endpoint — auth, lifecycle, relay |
| `lib/api/router_registry.py` | Modify | detect `ws_router` on route modules; mount directly on `app` |
| `main.py` | Modify | instantiate `ConnectionManager`; call `ws_route.set_manager()` |
| `tests/test_websocket.py` | Create | 6 focused tests |

## Authentication

Browsers cannot send `Authorization: Bearer` headers during the WebSocket upgrade handshake.
The JWT travels as a query parameter instead:

```
wss://host:8080/ws/{room_id}?token=<JWT>
```

The endpoint calls `decode_token(token)` before accepting the connection. On failure it closes
with code `4001` (application-level Unauthorized) — the connection is never accepted into a room.
On success, user identity is extracted from JWT claims; no database lookup is needed.

The route is mounted directly on the FastAPI `app` (via `ws_router` in router_registry), bypassing
the v1 sub-router's Bearer middleware entirely. JWT validation is self-contained in the endpoint.

## Message Contract

All messages (both directions) are JSON and follow the existing `Event` shape:

```json
{ "type": "room.joined", "payload": { "user_id": "...", "username": "..." } }
{ "type": "move.submit",  "payload": { "card_id": "..." } }
{ "type": "game.state",   "payload": { "round": 2, "scores": {} } }
```

- `type` is a dotted string by convention: `domain.event`
- `payload` is a free-form dict; consumers define its schema
- Room ID is in the URL path — not repeated inside every message
- This is identical to the in-process `Event` contract; future bridges between EventBus and
  WebSocket require zero translation

Server-generated lifecycle events:

| Event type | Direction | When |
|---|---|---|
| `room.joined` | server → room | client connects successfully |
| `room.left`   | server → room | client disconnects |

## ConnectionManager

```python
class ConnectionManager:
    """Domain-agnostic room manager. Owns no application logic.

    Thread-safety: all public methods are called from the async event loop.
    Dead connections are pruned lazily on the next broadcast — no background thread.
    """

    def __init__(self):
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, room_id: str, ws: WebSocket) -> None:
        """Accept the WebSocket and register it in the room."""
        await ws.accept()
        self._rooms[room_id].add(ws)

    def disconnect(self, room_id: str, ws: WebSocket) -> None:
        """Remove the connection; prune the room if empty."""
        self._rooms[room_id].discard(ws)
        if not self._rooms[room_id]:
            self._rooms.pop(room_id, None)

    async def broadcast(self, room_id: str, message: dict) -> None:
        """Send message to every live connection in room_id.
        Dead connections are silently removed."""
        dead = set()
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
        """Return the list of active room IDs."""
        return list(self._rooms)

    def room_size(self, room_id: str) -> int:
        """Return the number of active connections in a room."""
        return len(self._rooms.get(room_id, set()))
```

## WebSocket Route

```python
# lib/api/routes/ws.py
_manager: ConnectionManager | None = None

def set_manager(m: ConnectionManager) -> None:
    """Called once at startup from main.py."""
    global _manager
    _manager = m

ws_router = APIRouter()   # picked up by router_registry as ws_router

@ws_router.websocket("/{room_id}")
async def ws_endpoint(room_id: str, ws: WebSocket, token: str = Query(...)):
    # 1. Authenticate
    try:
        claims = decode_token(token)
    except JWTError:
        await ws.close(code=4001)
        return

    user = {"id": claims["sub"], "roles": claims.get("roles", [])}

    # 2. Join room
    await _manager.connect(room_id, ws)
    await _manager.broadcast(room_id, {"type": "room.joined", "payload": {"user": user}})

    # 3. Relay loop — application routes extend this by dispatching on data["type"]
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

## Router Registry Change

`router_registry.py` checks for a `ws_router` attribute and mounts it directly on `app`:

```python
if hasattr(sub, "ws_router"):
    app.include_router(sub.ws_router, prefix="/ws")
```

The `/ws` prefix is applied once here — route files use bare paths like `/{room_id}`.

## main.py Wiring

```python
from lib.api.websocket.manager import ConnectionManager
from lib.api.routes import ws as ws_route

manager = ConnectionManager()
ws_route.set_manager(manager)
```

`manager` can also be passed into `props_factory` if Flet views need to inspect room state
(e.g., show "3 players online" in a lobby UI) — it's just a plain Python object.

## Extending for a New Project

Adding a new real-time feature (e.g., a live dashboard) requires no changes to
`ConnectionManager` or the base relay. Two patterns:

**Pattern A — extend the relay with a dispatcher**
Replace the generic relay loop in `ws.py` with a dispatcher that calls different service
methods based on `data["type"]`. The `ConnectionManager` is passed to those handlers.

**Pattern B — new route file**
Create `lib/api/routes/dashboard_ws.py` with its own `ws_router`. It gets its own prefix
(e.g., `/ws/dashboard/{channel_id}`) via router_registry. Shares the same `ConnectionManager`
singleton, so admin dashboards can even peek into game rooms.

## Tests

```
tests/test_websocket.py

test_ws_rejects_missing_token
  → connect without ?token → connection closed with code 4001

test_ws_rejects_invalid_token
  → connect with tampered JWT → connection closed with code 4001

test_ws_connect_joins_room
  → valid JWT + connect → receives {"type": "room.joined", "payload": {"user": {...}}}

test_ws_broadcast_reaches_all_clients
  → two clients in same room → first sends message → both receive it

test_ws_disconnect_broadcasts_room_left
  → client A and B in room → A disconnects → B receives {"type": "room.left"}

test_ws_clients_in_different_rooms_isolated
  → client A in room-1, client B in room-2 → A sends message → B does not receive it
```

## Out of Scope

- Redis pub/sub bridge (add later if scaling beyond one Uvicorn worker)
- EventBus bridge (add later if services need to push to rooms without a WS route handler)
- Per-room capacity limits
- Reconnection/resume semantics
- Binary message framing
