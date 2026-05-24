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

import json

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
    # 0. Guard — ensure manager is initialized
    if _manager is None:
        await ws.close(code=1011)  # 1011 = Internal Error
        return

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
            try:
                data = await ws.receive_json()
            except json.JSONDecodeError:
                continue  # ignore malformed frames, keep connection alive
            if not isinstance(data, dict):
                continue  # ignore non-dict JSON, keep connection alive
            await _manager.broadcast(room_id, {
                "type": data.get("type", "message"),
                "payload": {**data.get("payload", {}), "from": user["id"]},
            })
    except WebSocketDisconnect:
        _manager.disconnect(room_id, ws)
        await _manager.broadcast(room_id, {"type": "room.left", "payload": {"user": user}})
