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


def _sanitize_provider_message(
    value: object,
    *,
    secrets_to_redact: tuple[str, ...] = (),
) -> str | None:
    if not isinstance(value, str):
        return None
    sanitized = value.strip().replace("\n", " ").replace("\r", " ")
    for secret in secrets_to_redact:
        if secret:
            sanitized = sanitized.replace(secret, "[REDACTED]")
    return sanitized[:200] or None


def _operation_succeeded(
    response: httpx.Response,
    *,
    secrets_to_redact: tuple[str, ...] = (),
) -> tuple[bool, str | None]:
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError:
        return False, "MAX subscriptions API returned malformed JSON"

    if isinstance(payload, dict) and "success" in payload:
        if payload.get("success") is True:
            return True, None
        message = _sanitize_provider_message(payload.get("message"), secrets_to_redact=secrets_to_redact)
        return False, message or "MAX subscriptions API returned unsuccessful response"

    return True, None


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
                if current:
                    response = await client.delete(MAX_SUBSCRIPTIONS_URL, params={"url": webhook_url}, headers=headers)
                    if response.status_code != 404:
                        ok, error = _operation_succeeded(response, secrets_to_redact=(token, webhook_secret))
                        if not ok:
                            return "error", error
                return "disabled", None

            payload = {"url": webhook_url, "update_types": MAX_EVENTS, "secret": webhook_secret}
            response = await client.post(MAX_SUBSCRIPTIONS_URL, json=payload, headers=headers)
            ok, error = _operation_succeeded(response, secrets_to_redact=(token, webhook_secret))
            if not ok:
                return "error", error
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
