"""Normalization helpers for Avito updates."""

from __future__ import annotations

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


def normalize_avito_update(bot_id: int, channel_id: int, update: dict) -> NormalizedIncomingMessage:
    """Convert an Avito webhook update into a NormalizedIncomingMessage."""

    payload_value = update.get("payload", {}).get("value")

    if payload_value:
        external_user_id = payload_value.get("user_id") or payload_value.get("user") or ""
        external_chat_id = payload_value.get("chat_id") or payload_value.get("conversation_id") or ""
        external_message_id = payload_value.get("id") or payload_value.get("message_id")
        content = payload_value.get("content") or {}
        text = (content.get("text") if isinstance(content, dict) else None) or ""
    else:
        external_user_id = update.get("user_id") or update.get("user") or ""
        external_chat_id = update.get("chat_id") or update.get("conversation_id") or external_user_id
        external_message_id = update.get("message_id") or update.get("id")
        text = update.get("text") or update.get("message") or ""

    external_chat_id = external_chat_id or external_user_id
    text = text or ""

    return NormalizedIncomingMessage(
        bot_id=bot_id,
        channel_id=channel_id,
        channel_type=ChannelType.AVITO,
        external_chat_id=str(external_chat_id),
        external_user_id=str(external_user_id),
        external_message_id=str(external_message_id) if external_message_id is not None else None,
        text=text,
        payload={"raw_update": update},
    )
