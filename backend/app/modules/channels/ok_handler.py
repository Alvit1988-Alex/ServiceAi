"""Normalization helpers for Odnoklassniki webhook payloads."""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


def _parse_timestamp_ms(value) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        timestamp_ms = int(value)
    except (TypeError, ValueError):
        return None
    try:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).replace(tzinfo=None)
    except (OverflowError, OSError, ValueError):
        return None


def normalize_ok_webhook(bot_id: int, channel_id: int, payload: dict) -> NormalizedIncomingMessage:
    event = payload or {}
    recipient = event.get("recipient") or {}
    sender = event.get("sender") or {}
    message = event.get("message") or {}

    external_chat_id = recipient.get("chat_id") or ""
    external_user_id = sender.get("user_id") or ""
    external_message_id = message.get("mid")
    text = message.get("text") or ""

    return NormalizedIncomingMessage(
        bot_id=bot_id,
        channel_id=channel_id,
        channel_type=ChannelType.OK,
        external_chat_id=str(external_chat_id),
        external_user_id=str(external_user_id),
        external_message_id=str(external_message_id) if external_message_id is not None else None,
        text=str(text),
        timestamp=_parse_timestamp_ms(event.get("timestamp")),
        payload={"raw_update": event},
    )
