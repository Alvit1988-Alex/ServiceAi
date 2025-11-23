"""Normalization helpers for webchat messages."""

from __future__ import annotations

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


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
