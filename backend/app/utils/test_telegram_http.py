from __future__ import annotations

import pytest

from app.config import settings
from app.modules.channels.models import BotChannel, ChannelType
from app.modules.channels import service as channels_service
from app.modules.channels.telegram_handler import send_telegram_message
from app.utils.telegram_http import (
    build_telegram_api_url,
    build_telegram_request_headers,
)


@pytest.fixture(autouse=True)
def reset_telegram_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_api_base_url", "https://api.telegram.org")
    monkeypatch.setattr(settings, "telegram_gateway_api_key", None)
    monkeypatch.setattr(settings, "telegram_webhook_base_url", None)
    monkeypatch.setattr(settings, "telegram_auth_webhook_base_url", None)
    monkeypatch.setattr(settings, "public_base_url", None)
    monkeypatch.setattr(settings, "telegram_webhook_secret", None)


def test_default_telegram_api_url() -> None:
    assert build_telegram_api_url("TOKEN", "getMe") == "https://api.telegram.org/botTOKEN/getMe"


def test_custom_gateway_api_url_strips_trailing_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_api_base_url", "https://tg.dialogus-ai.ru/")

    assert build_telegram_api_url("TOKEN", "sendMessage") == "https://tg.dialogus-ai.ru/botTOKEN/sendMessage"


def test_gateway_headers_only_when_key_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert build_telegram_request_headers() == {}

    monkeypatch.setattr(settings, "telegram_gateway_api_key", "secret-key")

    assert build_telegram_request_headers() == {"X-Dialogus-Gateway-Key": "secret-key"}


def test_telegram_webhook_base_url_takes_precedence_without_api_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_base_url", "https://service.dialogus-ai.ru")
    monkeypatch.setattr(
        settings, "telegram_webhook_base_url", "https://tg.dialogus-ai.ru/"
    )

    assert channels_service._get_telegram_webhook_base_url() == "https://tg.dialogus-ai.ru"


def test_telegram_webhook_base_url_fallback_preserves_public_api_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_base_url", "https://service.dialogus-ai.ru")

    assert channels_service._get_telegram_webhook_base_url() == "https://service.dialogus-ai.ru/api"


@pytest.mark.asyncio
async def test_send_telegram_message_passes_gateway_headers_without_changing_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(settings, "telegram_api_base_url", "https://tg.dialogus-ai.ru/")
    monkeypatch.setattr(settings, "telegram_gateway_api_key", "secret-key")

    class FakeResponse:
        pass

    expected_response = FakeResponse()

    class FakeAsyncClient:
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
            json: dict[str, str],
            headers: dict[str, str],
        ) -> FakeResponse:
            calls.append(
                {"url": url, "json": json, "headers": headers, "timeout": self.timeout}
            )
            return expected_response

    monkeypatch.setattr(
        "app.modules.channels.telegram_handler.httpx.AsyncClient", FakeAsyncClient
    )

    response = await send_telegram_message("TOKEN", "123", "hello")

    assert response is expected_response
    assert calls == [
        {
            "url": "https://tg.dialogus-ai.ru/botTOKEN/sendMessage",
            "json": {"chat_id": "123", "text": "hello"},
            "headers": {"X-Dialogus-Gateway-Key": "secret-key"},
            "timeout": 10,
        }
    ]


@pytest.mark.asyncio
async def test_sync_telegram_webhook_uses_dedicated_webhook_base_and_gateway_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(settings, "telegram_api_base_url", "https://tg.dialogus-ai.ru")
    monkeypatch.setattr(settings, "telegram_gateway_api_key", "secret-key")
    monkeypatch.setattr(
        settings, "telegram_webhook_base_url", "https://tg.dialogus-ai.ru/"
    )

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, bool]:
            return {"ok": True}

    class FakeAsyncClient:
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
            params: dict[str, str | None],
            headers: dict[str, str],
        ) -> FakeResponse:
            calls.append({"url": url, "params": params, "headers": headers})
            return FakeResponse()

    monkeypatch.setattr(
        "app.modules.channels.service.httpx.AsyncClient", FakeAsyncClient
    )
    channel = BotChannel(
        id=10,
        bot_id=20,
        channel_type=ChannelType.TELEGRAM,
        is_active=True,
        config={"token": "TOKEN", "secret_token": "secret-token"},
    )

    assert await channels_service.sync_telegram_webhook(channel) == ("ok", None)
    assert calls == [
        {
            "url": "https://tg.dialogus-ai.ru/botTOKEN/setWebhook",
            "params": {
                "url": "https://tg.dialogus-ai.ru/webhooks/telegram/20",
                "secret_token": "secret-token",
            },
            "headers": {"X-Dialogus-Gateway-Key": "secret-key"},
        }
    ]


def test_auth_webhook_base_url_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "public_base_url", "https://service.dialogus-ai.ru")
    monkeypatch.setattr(
        settings, "telegram_auth_webhook_base_url", "https://tg.dialogus-ai.ru/"
    )
    monkeypatch.setattr(settings, "telegram_webhook_path", "/auth/telegram/webhook")

    from app.utils.telegram_http import build_telegram_auth_webhook_url

    assert (
        build_telegram_auth_webhook_url()
        == "https://tg.dialogus-ai.ru/auth/telegram/webhook"
    )


def test_auth_webhook_base_url_falls_back_to_public_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_base_url", "https://service.dialogus-ai.ru")
    monkeypatch.setattr(settings, "telegram_auth_webhook_base_url", None)
    monkeypatch.setattr(settings, "telegram_webhook_path", "/auth/telegram/webhook")

    from app.utils.telegram_http import build_telegram_auth_webhook_url

    assert (
        build_telegram_auth_webhook_url()
        == "https://service.dialogus-ai.ru/auth/telegram/webhook"
    )
