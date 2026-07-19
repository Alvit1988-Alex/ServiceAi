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


def get_telegram_auth_bot_id() -> int | None:
    """Return the numeric auth bot id encoded in the bot token, if configured."""

    token = settings.telegram_auth_bot_token
    if not token or ":" not in token:
        return None

    raw_bot_id = token.split(":", 1)[0]
    if not raw_bot_id.isdigit():
        return None
    return int(raw_bot_id)


def build_telegram_auth_webhook_url() -> str | None:
    """Build the external webhook URL used when registering the auth bot."""

    if settings.telegram_auth_webhook_base_url:
        bot_id = get_telegram_auth_bot_id()
        if bot_id is None:
            return None
        webhook_url = f"{settings.telegram_auth_webhook_base_url.rstrip('/')}/webhooks/telegram/{bot_id}"
    else:
        base_url = settings.public_base_url
        if not base_url:
            return None

        path = settings.telegram_webhook_path or "/auth/telegram/webhook"
        if not path.startswith("/"):
            path = f"/{path}"
        webhook_url = f"{base_url.rstrip('/')}{path}"

    if settings.telegram_webhook_secret:
        return f"{webhook_url}?secret={settings.telegram_webhook_secret}"
    return webhook_url
