"""Normalization helpers for Avito updates."""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


def _parse_timestamp(value) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except Exception:
            return None

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    return None


def normalize_avito_update(bot_id: int, channel_id: int, update: dict) -> NormalizedIncomingMessage:
    """Convert an Avito webhook update into a NormalizedIncomingMessage."""

    payload = update.get("payload") or {}
    payload_value = payload.get("value") or {}

    source = payload_value if payload_value else update

    external_user_id = (
        payload_value.get("user_id")
        or payload_value.get("user")
        or payload_value.get("author_id")
        or source.get("user_id")
        or source.get("user")
        or ""
    )
    external_chat_id = (
        payload_value.get("chat_id")
        or payload_value.get("conversation_id")
        or source.get("chat_id")
        or source.get("conversation_id")
        or external_user_id
    )
    external_message_id = (
        payload_value.get("id")
        or payload_value.get("message_id")
        or source.get("message_id")
        or source.get("id")
    )

    content = payload_value.get("content") if isinstance(payload_value, dict) else {}
    text = (content.get("text") if isinstance(content, dict) else None) or source.get("text") or ""
    item_id = (
        payload_value.get("item_id")
        or payload_value.get("itemId")
        or source.get("item_id")
        or source.get("itemId")
    )
    timestamp_value = (
        payload_value.get("timestamp")
        or payload_value.get("created_at")
        or source.get("timestamp")
        or source.get("created_at")
    )

    direction = payload_value.get("direction") or source.get("direction")
    message_type = payload_value.get("type") or source.get("type")

    skip_reason = None
    if message_type == "system":
        skip_reason = "system_message"
    if direction and str(direction).lower() == "out":
        skip_reason = skip_reason or "outgoing_message"

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
        item_id=str(item_id) if item_id is not None else None,
        timestamp=_parse_timestamp(timestamp_value),
        payload={
            "raw_update": update,
            "item_id": item_id,
            "direction": direction,
            "message_type": message_type,
            "skip_processing": bool(skip_reason),
            "skip_reason": skip_reason,
        },
    )
