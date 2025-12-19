"""Helpers for subscribing Avito Messenger webhooks."""
from __future__ import annotations

import logging
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.modules.channels.models import BotChannel

logger = logging.getLogger(__name__)

AVITO_WEBHOOK_SUBSCRIBE_URL = "https://api.avito.ru/messenger/v3/webhook"
AVITO_WEBHOOK_UNSUBSCRIBE_URL = "https://api.avito.ru/messenger/v1/webhook/unsubscribe"


def _build_webhook_url(channel: BotChannel, public_base_url: str, webhook_secret: str) -> str:
    return f"{public_base_url.rstrip('/')}/bots/{channel.bot_id}/channels/webhooks/avito/{channel.id}?secret={webhook_secret}"


async def _get_access_token(channel: BotChannel) -> str | None:
    from app.modules.channels.avito_auth import get_valid_access_token, request_access_token

    token = await get_valid_access_token(channel)
    if token:
        return token
    return await request_access_token(channel)


async def subscribe(channel: BotChannel, public_base_url: str, webhook_secret: str | None = None) -> None:
    secret = webhook_secret or (channel.config or {}).get("webhook_secret") or (channel.config or {}).get("secret")
    if not secret:
        logger.warning(
            "Avito webhook subscribe skipped: missing webhook secret",
            extra={"bot_id": channel.bot_id, "channel_id": channel.id},
        )
        return

    access_token = await _get_access_token(channel)
    if not access_token:
        logger.error(
            "Avito webhook subscribe failed: access token unavailable",
            extra={"bot_id": channel.bot_id, "channel_id": channel.id},
        )
        return

    webhook_url = _build_webhook_url(channel, public_base_url, secret)
    payload = {"url": webhook_url}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                AVITO_WEBHOOK_SUBSCRIBE_URL, json=payload, headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            safe_url = urlunsplit(urlsplit(webhook_url)._replace(query=""))
            logger.info(
                "Avito webhook subscribed",
                extra={"bot_id": channel.bot_id, "channel_id": channel.id, "url": safe_url},
            )
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Failed to subscribe Avito webhook: HTTP error",
            exc_info=exc,
            extra={
                "bot_id": channel.bot_id,
                "channel_id": channel.id,
                "status": exc.response.status_code if exc.response else None,
                "response": exc.response.text if exc.response else None,
            },
        )
    except httpx.RequestError as exc:
        logger.error(
            "Failed to subscribe Avito webhook: request error",
            exc_info=exc,
            extra={"bot_id": channel.bot_id, "channel_id": channel.id},
        )
    except Exception:
        logger.exception(
            "Unexpected error during Avito webhook subscribe",
            extra={"bot_id": channel.bot_id, "channel_id": channel.id},
        )


async def unsubscribe(channel: BotChannel, public_base_url: str, webhook_secret: str | None = None) -> None:
    secret = webhook_secret or (channel.config or {}).get("webhook_secret") or (channel.config or {}).get("secret")
    if not secret:
        logger.warning(
            "Avito webhook unsubscribe skipped: missing webhook secret",
            extra={"bot_id": channel.bot_id, "channel_id": channel.id},
        )
        return

    access_token = await _get_access_token(channel)
    if not access_token:
        logger.error(
            "Avito webhook unsubscribe failed: access token unavailable",
            extra={"bot_id": channel.bot_id, "channel_id": channel.id},
        )
        return

    webhook_url = _build_webhook_url(channel, public_base_url, secret)
    payload = {"url": webhook_url}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                AVITO_WEBHOOK_UNSUBSCRIBE_URL,
                json=payload,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            safe_url = urlunsplit(urlsplit(webhook_url)._replace(query=""))
            logger.info(
                "Avito webhook unsubscribed",
                extra={"bot_id": channel.bot_id, "channel_id": channel.id, "url": safe_url},
            )
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Failed to unsubscribe Avito webhook: HTTP error",
            exc_info=exc,
            extra={
                "bot_id": channel.bot_id,
                "channel_id": channel.id,
                "status": exc.response.status_code if exc.response else None,
                "response": exc.response.text if exc.response else None,
            },
        )
    except httpx.RequestError as exc:
        logger.error(
            "Failed to unsubscribe Avito webhook: request error",
            exc_info=exc,
            extra={"bot_id": channel.bot_id, "channel_id": channel.id},
        )
    except Exception:
        logger.exception(
            "Unexpected error during Avito webhook unsubscribe",
            extra={"bot_id": channel.bot_id, "channel_id": channel.id},
        )
