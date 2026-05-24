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
