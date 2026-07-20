from __future__ import annotations

import asyncio

import pytest

from app.config import settings
from app.scripts.register_telegram_auth_webhook import register_telegram_auth_webhook


@pytest.fixture(autouse=True)
def reset_telegram_auth_webhook_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_api_base_url", "https://tg.dialogus-ai.ru")
    monkeypatch.setattr(settings, "telegram_gateway_api_key", "gateway-secret")
    monkeypatch.setattr(settings, "telegram_auth_webhook_base_url", "https://tg.dialogus-ai.ru")
    monkeypatch.setattr(settings, "telegram_webhook_path", "/auth/telegram/webhook")
    monkeypatch.setattr(settings, "telegram_auth_bot_token", "TOKEN")
    monkeypatch.setattr(settings, "telegram_webhook_secret", "webhook-secret")


class FakeResponse:
    is_success = True
    status_code = 200


class FakeAsyncClient:
    calls: list[dict[str, object]] = []

    def __init__(self, *, timeout: int) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post(
        self,
        url: str,
        *,
        data: dict[str, str],
        headers: dict[str, str],
    ) -> FakeResponse:
        self.calls.append(
            {"url": url, "data": data, "headers": headers, "timeout": self.timeout}
        )
        return FakeResponse()


def test_register_telegram_auth_webhook_uses_secret_token_and_gateway_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setattr(
        "app.scripts.register_telegram_auth_webhook.httpx.AsyncClient",
        FakeAsyncClient,
    )

    assert asyncio.run(register_telegram_auth_webhook()) is True

    assert FakeAsyncClient.calls == [
        {
            "url": "https://tg.dialogus-ai.ru/botTOKEN/setWebhook",
            "data": {
                "url": "https://tg.dialogus-ai.ru/auth/telegram/webhook",
                "secret_token": "webhook-secret",
            },
            "headers": {"X-Dialogus-Gateway-Key": "gateway-secret"},
            "timeout": 10,
        }
    ]
    assert "webhook-secret" not in str(FakeAsyncClient.calls[0]["url"])


def test_register_telegram_auth_webhook_omits_absent_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setattr(settings, "telegram_webhook_secret", None)
    monkeypatch.setattr(
        "app.scripts.register_telegram_auth_webhook.httpx.AsyncClient",
        FakeAsyncClient,
    )

    assert asyncio.run(register_telegram_auth_webhook()) is True

    assert FakeAsyncClient.calls[0]["data"] == {
        "url": "https://tg.dialogus-ai.ru/auth/telegram/webhook"
    }
