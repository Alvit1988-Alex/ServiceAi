"""WebSocket manager stub."""

from typing import Dict, Set, Tuple

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self._admin_connections: Dict[int, Set[WebSocket]] = {}
        self._webchat_connections: Dict[Tuple[int, str], Set[WebSocket]] = {}

    async def connect_admin(self, admin_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._admin_connections.setdefault(admin_id, set()).add(ws)

    async def disconnect_admin(self, admin_id: int, ws: WebSocket) -> None:
        conns = self._admin_connections.get(admin_id, set())
        conns.discard(ws)

    async def broadcast_to_all_admins(self, message: dict) -> None:
        for conns in self._admin_connections.values():
            for ws in conns:
                await ws.send_json(message)

    async def connect_webchat(self, bot_id: int, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        key = (bot_id, session_id)
        self._webchat_connections.setdefault(key, set()).add(ws)

    async def disconnect_webchat(self, bot_id: int, session_id: str, ws: WebSocket) -> None:
        key = (bot_id, session_id)
        conns = self._webchat_connections.get(key, set())
        conns.discard(ws)

    async def send_to_webchat(self, bot_id: int, session_id: str, message: dict) -> None:
        key = (bot_id, session_id)
        for ws in self._webchat_connections.get(key, set()):
            await ws.send_json(message)
