"""Normalization helpers for webchat messages."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.service import AIService
from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage
from app.modules.dialogs.schemas import DialogMessageOut, DialogOut
from app.modules.dialogs.service import DialogsService
from app.modules.dialogs.websocket_manager import WebSocketManager


def normalize_webchat_message(bot_id: int, channel_id: int, payload: dict) -> NormalizedIncomingMessage:
    """Normalize a webchat payload into a NormalizedIncomingMessage."""

    session_id = str(payload.get("session_id") or payload.get("user") or "")
    text = payload.get("text") or payload.get("message") or ""

    return NormalizedIncomingMessage(
        bot_id=bot_id,
        channel_id=channel_id,
        channel_type=ChannelType.WEBCHAT,
        external_chat_id=session_id,
        external_user_id=session_id,
        external_message_id=str(payload.get("message_id")) if payload.get("message_id") else None,
        text=text,
        payload={"raw_update": payload},
    )


async def handle_webchat_ws_message(
    *,
    bot_id: int,
    channel_id: int,
    session_id: str,
    data: dict,
    text: str,
    session: AsyncSession,
    dialogs_service: DialogsService,
    ai_service: AIService,
    manager: WebSocketManager,
) -> None:
    payload = dict(data)
    payload["text"] = text
    payload.setdefault("session_id", session_id)

    normalized = normalize_webchat_message(
        bot_id=bot_id,
        channel_id=channel_id,
        payload=payload,
    )

    user_message, bot_message, dialog, dialog_created = await dialogs_service.process_incoming_message(
        session=session,
        incoming_message=normalized,
        ai_service=ai_service,
    )

    await _send_webchat_updates(
        manager=manager,
        bot_id=bot_id,
        session_id=session_id,
        dialog=dialog,
        dialog_created=dialog_created,
        messages=[message for message in (user_message, bot_message) if message is not None],
    )


async def _send_webchat_updates(
    *,
    manager: WebSocketManager,
    bot_id: int,
    session_id: str,
    dialog,
    dialog_created: bool,
    messages: list,
) -> None:
    dialog_payload = DialogOut.model_validate(dialog).model_dump()

    if dialog_created:
        await manager.send_to_webchat(
            bot_id=bot_id,
            session_id=session_id,
            message={"event": "dialog_created", "data": dialog_payload},
        )

    for message in messages:
        message_payload = DialogMessageOut.model_validate(message).model_dump()
        await manager.send_to_webchat(
            bot_id=bot_id,
            session_id=session_id,
            message={"event": "message_created", "data": message_payload},
        )
        await manager.send_to_webchat(
            bot_id=bot_id,
            session_id=session_id,
            message={"event": "dialog_updated", "data": dialog_payload},
        )
