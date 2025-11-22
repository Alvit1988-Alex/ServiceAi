"""WebSocket connection manager."""

from collections import defaultdict
from typing import DefaultDict, Set, Tuple

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class WebSocketManager:
    def __init__(self) -> None:
        self._admin_connections: Set[WebSocket] = set()
        self._webchat_connections: DefaultDict[Tuple[int, str], Set[WebSocket]] = defaultdict(set)

    async def connect_admin(self, ws: WebSocket) -> None:
        await ws.accept()
        self._admin_connections.add(ws)

    async def disconnect_admin(self, ws: WebSocket) -> None:
        self._admin_connections.discard(ws)

    async def broadcast_to_admins(self, message: dict) -> None:
        disconnected: Set[WebSocket] = set()
        for ws in self._admin_connections:
            if ws.application_state != WebSocketState.CONNECTED:
                disconnected.add(ws)
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)

        for ws in disconnected:
            self._admin_connections.discard(ws)

    async def connect_webchat(self, bot_id: int, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._webchat_connections[(bot_id, session_id)].add(ws)

    async def disconnect_webchat(self, bot_id: int, session_id: str, ws: WebSocket) -> None:
        key = (bot_id, session_id)
        connections = self._webchat_connections.get(key)
        if not connections:
            return

        connections.discard(ws)
        if not connections:
            self._webchat_connections.pop(key, None)

    async def broadcast_to_webchat(self, bot_id: int, session_id: str, message: dict) -> None:
        key = (bot_id, session_id)
        connections = self._webchat_connections.get(key, set())
        disconnected: Set[WebSocket] = set()

        for ws in connections:
            if ws.application_state != WebSocketState.CONNECTED:
                disconnected.add(ws)
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)

        for ws in disconnected:
            connections.discard(ws)

        if not connections:
            self._webchat_connections.pop(key, None)


manager = WebSocketManager()
