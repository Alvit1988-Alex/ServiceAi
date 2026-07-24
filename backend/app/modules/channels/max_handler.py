"""Normalization helpers for Max platform webhooks."""

from __future__ import annotations

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _clean_id(value: object) -> str | None:
    if value is None:
        return None
    value_str = str(value).strip()
    return value_str or None


def _extract_bot_started_payload(payload: dict) -> tuple[object, object, object, object]:
    user = _as_dict(payload.get("user") or payload.get("sender"))
    recipient = _as_dict(payload.get("recipient") or payload.get("chat"))
    external_user_id = user.get("user_id") or payload.get("user_id")
    external_chat_id = recipient.get("chat_id") or recipient.get("user_id") or payload.get("chat_id") or external_user_id
    text = (
        payload.get("payload")
        or payload.get("start_payload")
        or payload.get("deeplink_payload")
        or payload.get("parameter")
    )
    return external_user_id, external_chat_id, payload.get("timestamp"), text


def normalize_max_webhook(bot_id: int, channel_id: int, payload: dict) -> NormalizedIncomingMessage | None:
    """Convert a Max webhook payload into a NormalizedIncomingMessage."""

    if not isinstance(payload, dict):
        return None

    update_type = payload.get("update_type")
    external_message_id = None
    timestamp = payload.get("timestamp")

    if update_type == "message_created":
        message = _as_dict(payload.get("message"))
        sender = _as_dict(message.get("sender"))
        recipient = _as_dict(message.get("recipient"))
        body = _as_dict(message.get("body"))

        external_user_id = sender.get("user_id")
        external_chat_id = recipient.get("chat_id") or recipient.get("user_id")
        external_message_id = body.get("mid")
        text = body.get("text")
    elif update_type == "bot_started":
        external_user_id, external_chat_id, timestamp, text = _extract_bot_started_payload(payload)
    else:
        return None

    user_id = _clean_id(external_user_id)
    chat_id = _clean_id(external_chat_id)
    message_text = _clean_text(text)
    if not user_id or not chat_id or not message_text:
        return None

    return NormalizedIncomingMessage(
        bot_id=bot_id,
        channel_id=channel_id,
        channel_type=ChannelType.MAX,
        external_chat_id=chat_id,
        external_user_id=user_id,
        external_message_id=_clean_id(external_message_id),
        text=message_text,
        payload={"raw_update": payload, "timestamp": timestamp} if timestamp is not None else {"raw_update": payload},
    )
