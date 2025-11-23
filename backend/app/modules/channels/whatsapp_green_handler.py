"""Normalization helpers for WhatsApp Green API notifications."""

from __future__ import annotations

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


def _extract_green_message(notification: dict) -> dict | None:
    messages = notification.get("messages")
    if isinstance(messages, list) and messages:
        return messages[0]
    return notification.get("message")


def normalize_whatsapp_green_notification(
    bot_id: int, channel_id: int, notification: dict
) -> NormalizedIncomingMessage:
    """Convert a WhatsApp Green API webhook notification to a normalized message."""

    message = _extract_green_message(notification) or {}
    text = ""

    if isinstance(message.get("text"), dict):
        text = message.get("text", {}).get("body", "")
    elif message.get("text"):
        text = str(message.get("text"))
    elif notification.get("text"):
        text = str(notification.get("text"))

    external_user_id = message.get("from") or notification.get("from") or notification.get("user") or ""
    external_message_id = message.get("id") or notification.get("message_id")

    return NormalizedIncomingMessage(
        bot_id=bot_id,
        channel_id=channel_id,
        channel_type=ChannelType.WHATSAPP_GREEN,
        external_chat_id=str(external_user_id),
        external_user_id=str(external_user_id),
        external_message_id=str(external_message_id) if external_message_id is not None else None,
        text=text,
        payload={"raw_update": notification},
    )
