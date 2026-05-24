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


def test_manager_broadcast_prunes_empty_room_from_rooms(manager):
    dead = _DeadWs()
    asyncio.run(manager.connect("room1", dead))
    asyncio.run(manager.broadcast("room1", {"type": "ping", "payload": {}}))
    assert "room1" not in manager.rooms()


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
