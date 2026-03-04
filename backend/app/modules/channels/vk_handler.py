"""Normalization helpers for VK Callback API payloads."""

from __future__ import annotations

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


def normalize_vk_callback(bot_id: int, channel_id: int, payload: dict) -> NormalizedIncomingMessage:
    """Convert VK callback payload into NormalizedIncomingMessage."""

    event = payload or {}
    event_object = event.get("object") or {}
    message = event_object.get("message") or {}

    external_chat_id = message.get("peer_id") or ""
    external_user_id = message.get("from_id") or ""
    external_message_id = message.get("id")
    text = message.get("text") or ""

    sanitized_payload = dict(event)
    sanitized_payload.pop("secret", None)

    return NormalizedIncomingMessage(
        bot_id=bot_id,
        channel_id=channel_id,
        channel_type=ChannelType.VK,
        external_chat_id=str(external_chat_id),
        external_user_id=str(external_user_id),
        external_message_id=str(external_message_id) if external_message_id is not None else None,
        text=str(text),
        payload={"raw_update": sanitized_payload},
    )
