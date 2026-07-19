"""CLI command to register the Telegram auth bot webhook."""

from __future__ import annotations

import asyncio

import httpx

from app.config import settings
from app.utils.telegram_http import (
    build_telegram_api_url,
    build_telegram_auth_webhook_url,
    build_telegram_request_headers,
)


async def register_telegram_auth_webhook() -> bool:
    """Register the configured auth bot webhook URL with Telegram."""

    if not settings.telegram_auth_bot_token:
        print("Telegram auth bot token is not configured")
        return False

    webhook_url = build_telegram_auth_webhook_url()
    if not webhook_url:
        print("Public base URL is not configured")
        return False

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            build_telegram_api_url(settings.telegram_auth_bot_token, "setWebhook"),
            data={"url": webhook_url},
            headers=build_telegram_request_headers(),
        )
    if response.is_success:
        print("Telegram auth webhook registered")
        return True

    print(f"Telegram auth webhook registration failed: {response.status_code}")
    return False


def main() -> None:
    asyncio.run(register_telegram_auth_webhook())


if __name__ == "__main__":
    main()
