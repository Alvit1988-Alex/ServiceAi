"""Shared helpers for Telegram Bot API request construction."""

from __future__ import annotations

from app.config import settings

_DIALOGUS_GATEWAY_HEADER = "X-Dialogus-Gateway-Key"


def build_telegram_api_url(token: str, method: str | None = None) -> str:
    """Build a Telegram-compatible Bot API URL for the configured API base."""

    base_url = settings.telegram_api_base_url.rstrip("/")
    url = f"{base_url}/bot{token}"
    if method:
        return f"{url}/{method.lstrip('/')}"
    return url


def build_telegram_request_headers() -> dict[str, str]:
    """Build optional Telegram Gateway headers for outbound Bot API calls."""

    gateway_key = settings.telegram_gateway_api_key
    if not gateway_key:
        return {}
    return {_DIALOGUS_GATEWAY_HEADER: gateway_key}


def build_telegram_auth_webhook_url() -> str | None:
    """Build the external webhook URL used when registering the auth bot."""

    base_url = settings.telegram_auth_webhook_base_url or settings.public_base_url
    if not base_url:
        return None

    path = settings.telegram_webhook_path or "/auth/telegram/webhook"
    if not path.startswith("/"):
        path = f"/{path}"

    return f"{base_url.rstrip('/')}{path}"
