"""Normalization helpers for Avito updates."""

from __future__ import annotations

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


def normalize_avito_update(bot_id: int, channel_id: int, update: dict) -> NormalizedIncomingMessage:
    """Convert an Avito webhook update into a NormalizedIncomingMessage."""

    external_user_id = update.get("user_id") or update.get("user") or ""
    external_message_id = update.get("message_id") or update.get("id")
    text = update.get("text") or update.get("message") or ""

    return NormalizedIncomingMessage(
        bot_id=bot_id,
        channel_id=channel_id,
        channel_type=ChannelType.AVITO,
        external_chat_id=str(external_user_id),
        external_user_id=str(external_user_id),
        external_message_id=str(external_message_id) if external_message_id is not None else None,
        text=text,
        payload={"raw_update": update},
    )
