"""Normalization helpers for Max platform webhooks."""

from __future__ import annotations

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


def normalize_max_webhook(bot_id: int, channel_id: int, payload: dict, headers: dict | None = None) -> NormalizedIncomingMessage:
    """Convert a Max webhook payload into a NormalizedIncomingMessage."""

    headers = headers or {}
    message = payload.get("message") or payload

    external_user_id = message.get("from") or payload.get("user") or headers.get("X-User-Id") or ""
    external_message_id = message.get("id") or payload.get("message_id") or payload.get("id")
    text = message.get("text") or payload.get("text") or ""

    if isinstance(text, dict):
        text = text.get("body") or ""

    return NormalizedIncomingMessage(
        bot_id=bot_id,
        channel_id=channel_id,
        channel_type=ChannelType.MAX,
        external_chat_id=str(external_user_id),
        external_user_id=str(external_user_id),
        external_message_id=str(external_message_id) if external_message_id is not None else None,
        text=text,
        payload={"raw_update": payload, "headers": headers},
    )
