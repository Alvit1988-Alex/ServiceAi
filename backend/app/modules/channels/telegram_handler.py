"""Normalization helpers for Telegram updates."""

from __future__ import annotations

import httpx

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


async def send_telegram_message(token: str, chat_id: str, text: str) -> httpx.Response:
    payload = {"chat_id": chat_id, "text": text}
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        return await client.post(url, json=payload)


def _extract_telegram_message(update: dict) -> tuple[dict | None, dict | None]:
    """Return the message-like object and user source from a Telegram update."""

    message = update.get("message") or update.get("edited_message")
    if message:
        return message, message.get("from")

    callback = update.get("callback_query")
    if callback:
        return callback.get("message"), callback.get("from")

    return None, update.get("from")


def normalize_telegram_update(bot_id: int, channel_id: int, update: dict) -> NormalizedIncomingMessage:
    """Convert a raw Telegram webhook update into a NormalizedIncomingMessage."""

    message, user = _extract_telegram_message(update)
    text = None
    external_message_id = None

    if message:
        text = message.get("text") or message.get("caption")
        external_message_id = message.get("message_id")
    elif update.get("callback_query"):
        callback = update["callback_query"]
        text = callback.get("data")
        external_message_id = callback.get("id")
    else:
        text = update.get("text")
        external_message_id = update.get("message_id") or update.get("id")

    external_user_id = None
    if user and user.get("id") is not None:
        external_user_id = str(user.get("id"))
    elif update.get("user") is not None:
        external_user_id = str(update.get("user"))

    chat = message.get("chat") if message else None
    external_chat_id = None
    if chat and chat.get("id") is not None:
        external_chat_id = str(chat.get("id"))
    elif update.get("chat_id") is not None:
        external_chat_id = str(update.get("chat_id"))

    return NormalizedIncomingMessage(
        bot_id=bot_id,
        channel_id=channel_id,
        channel_type=ChannelType.TELEGRAM,
        external_chat_id=external_chat_id or external_user_id or "",
        external_user_id=external_user_id or "",
        external_message_id=str(external_message_id) if external_message_id is not None else None,
        text=text if text is not None else "",
        payload={"raw_update": update},
    )
