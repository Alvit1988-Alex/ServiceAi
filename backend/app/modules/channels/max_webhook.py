"""Helpers for synchronizing Max subscriptions."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.modules.channels.models import BotChannel

logger = logging.getLogger(__name__)

MAX_API_BASE_URL = "https://platform-api2.max.ru"
MAX_SUBSCRIPTIONS_URL = f"{MAX_API_BASE_URL}/subscriptions"
MAX_EVENTS = ["message_created", "bot_started"]


def build_max_webhook_url(channel: BotChannel, public_api_base_url: str) -> str:
    return f"{public_api_base_url.rstrip('/')}/bots/{channel.bot_id}/channels/webhooks/max/{channel.id}"


def _safe_error(prefix: str, status_code: int | None = None) -> str:
    return f"{prefix}: HTTP {status_code}" if status_code else prefix


def _subscriptions_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("subscriptions", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _subscription_url(item: dict[str, Any]) -> str | None:
    url = item.get("url") or item.get("webhook_url") or item.get("callback_url")
    return str(url) if url else None


def _subscription_id(item: dict[str, Any]) -> str | None:
    value = item.get("id") or item.get("subscription_id")
    return str(value) if value is not None else None


async def sync_max_webhook(channel: BotChannel, public_api_base_url: str | None) -> tuple[str | None, str | None]:
    config = channel.config or {}
    token = config.get("token")
    webhook_secret = config.get("webhook_secret")

    if not token:
        return "pending", "MAX token is not configured"
    if not webhook_secret:
        return "error", "MAX webhook secret is not configured"
    if not public_api_base_url:
        return "pending", "Public base URL is not configured"

    webhook_url = build_max_webhook_url(channel, public_api_base_url)
    headers = {"Authorization": token, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            list_response = await client.get(MAX_SUBSCRIPTIONS_URL, headers=headers)
            list_response.raise_for_status()
            subscriptions = _subscriptions_list(list_response.json())
            current = [item for item in subscriptions if _subscription_url(item) == webhook_url]

            if not channel.is_active:
                for item in current:
                    sub_id = _subscription_id(item)
                    if sub_id:
                        response = await client.delete(f"{MAX_SUBSCRIPTIONS_URL}/{sub_id}", headers=headers)
                    else:
                        response = await client.delete(MAX_SUBSCRIPTIONS_URL, params={"url": webhook_url}, headers=headers)
                    if response.status_code not in {200, 202, 204, 404}:
                        response.raise_for_status()
                return "disabled", None

            if current:
                return "ok", None

            payload = {"url": webhook_url, "update_types": MAX_EVENTS, "secret": webhook_secret}
            response = await client.post(MAX_SUBSCRIPTIONS_URL, json=payload, headers=headers)
            response.raise_for_status()
            return "ok", None
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        logger.warning(
            "Max webhook sync failed with HTTP status",
            extra={"bot_id": channel.bot_id, "channel_id": channel.id, "status": status_code},
        )
        return "error", _safe_error("MAX subscriptions API error", status_code)
    except (httpx.RequestError, ValueError) as exc:
        logger.warning(
            "Max webhook sync failed",
            extra={"bot_id": channel.bot_id, "channel_id": channel.id, "error_type": type(exc).__name__},
        )
        return "error", "MAX subscriptions API request failed"
