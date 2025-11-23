"""Normalization helpers for WhatsApp 360dialog webhooks."""

from __future__ import annotations

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


def _extract_360_message(payload: dict) -> dict | None:
    messages = payload.get("messages")
    if isinstance(messages, list) and messages:
        return messages[0]
    return payload.get("message")


def normalize_whatsapp_360_webhook(bot_id: int, channel_id: int, payload: dict) -> NormalizedIncomingMessage:
    """Convert a WhatsApp 360dialog webhook payload to a normalized message."""

    message = _extract_360_message(payload) or {}
    text = ""

    if isinstance(message.get("text"), dict):
        text = message.get("text", {}).get("body", "")
    elif message.get("text"):
        text = str(message.get("text"))
    elif payload.get("text"):
        text = str(payload.get("text"))

    external_user_id = message.get("from") or payload.get("from") or payload.get("user") or ""
    external_message_id = message.get("id") or payload.get("message_id")

    return NormalizedIncomingMessage(
        bot_id=bot_id,
        channel_id=channel_id,
        channel_type=ChannelType.WHATSAPP_360,
        external_chat_id=str(external_user_id),
        external_user_id=str(external_user_id),
        external_message_id=str(external_message_id) if external_message_id is not None else None,
        text=text,
        payload={"raw_update": payload},
    )
