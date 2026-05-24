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
