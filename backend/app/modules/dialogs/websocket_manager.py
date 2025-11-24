"""WebSocket connection manager."""

from collections import defaultdict
from typing import DefaultDict, Iterable, Set, Tuple

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class WebSocketManager:
    def __init__(self) -> None:
        self._admin_connections: DefaultDict[int, Set[WebSocket]] = defaultdict(set)
        self._webchat_connections: DefaultDict[Tuple[int, str], Set[WebSocket]] = defaultdict(set)

    async def register_admin(self, admin_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._admin_connections[admin_id].add(ws)

    async def unregister_admin(self, admin_id: int, ws: WebSocket) -> None:
        connections = self._admin_connections.get(admin_id)
        if not connections:
            return

        connections.discard(ws)
        if not connections:
            self._admin_connections.pop(admin_id, None)

    async def broadcast_to_admin(self, admin_id: int, message: dict) -> None:
        await self.broadcast_to_admins(admin_ids=[admin_id], message=message)

    async def broadcast_to_admins(self, message: dict, admin_ids: Iterable[int] | None = None) -> None:
        target_admins = set(admin_ids) if admin_ids is not None else set(self._admin_connections.keys())
        for admin_id in target_admins:
            await self._broadcast_to_connections(self._admin_connections.get(admin_id, set()), message)

    async def register_webchat(self, bot_id: int, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._webchat_connections[(bot_id, session_id)].add(ws)

    async def unregister_webchat(self, bot_id: int, session_id: str, ws: WebSocket) -> None:
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
        await self._broadcast_to_connections(connections, message)
        if not connections:
            self._webchat_connections.pop(key, None)

    async def broadcast_new_message(
        self,
        *,
        dialog_payload: dict,
        message_payload: dict,
        admin_ids: Iterable[int] | None = None,
    ) -> None:
        await self.broadcast_to_admins({"event": "message_created", "data": message_payload}, admin_ids=admin_ids)
        await self.broadcast_to_admins({"event": "dialog_updated", "data": dialog_payload}, admin_ids=admin_ids)

        await self.broadcast_to_webchat(
            bot_id=dialog_payload["bot_id"],
            session_id=dialog_payload["external_chat_id"],
            message={"event": "message_created", "data": message_payload},
        )
        await self.broadcast_to_webchat(
            bot_id=dialog_payload["bot_id"],
            session_id=dialog_payload["external_chat_id"],
            message={"event": "dialog_updated", "data": dialog_payload},
        )

    async def _broadcast_to_connections(self, connections: Set[WebSocket], message: dict) -> None:
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


manager = WebSocketManager()
