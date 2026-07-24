import asyncio

import httpx
import pytest
from fastapi import HTTPException

from app.modules.channels.models import ChannelType
from app.modules.channels.service import ChannelsService, MaxTokenValidationUnavailableError


def test_prepare_max_config_generates_and_preserves_webhook_secret():
    service = ChannelsService()
    prepared = service._prepare_config(ChannelType.MAX, {})
    assert prepared["webhook_secret"]
    assert "token" not in prepared

    repeated = service._prepare_config(ChannelType.MAX, prepared)
    assert repeated["webhook_secret"] == prepared["webhook_secret"]


def test_prepare_max_config_migrates_auth_token_and_removes_legacy_fields():
    service = ChannelsService()
    prepared = service._prepare_config(
        ChannelType.MAX,
        {
            "auth_token": "old-token",
            "send_message_url": "https://example.invalid",
            "api_base_url": "https://example.invalid",
            "send_message_path": "/send",
            "secret": "legacy-secret",
        },
    )
    assert prepared["token"] == "old-token"
    for key in ("auth_token", "send_message_url", "api_base_url", "send_message_path", "secret"):
        assert key not in prepared


def test_prepare_max_config_keeps_token_over_auth_token():
    prepared = ChannelsService()._prepare_config(ChannelType.MAX, {"token": "new", "auth_token": "old"})
    assert prepared["token"] == "new"
    assert "auth_token" not in prepared


def test_validate_max_token_accepts_success(monkeypatch):
    calls = []

    class Client:
        def __init__(self, timeout):
            self.timeout = timeout
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def get(self, url, headers):
            calls.append((url, headers))
            return httpx.Response(
                200,
                json={"user_id": 123, "name": "Bot"},
                request=httpx.Request("GET", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    result = asyncio.run(ChannelsService._validate_max_token("credential-placeholder"))
    assert result == {"bot_id": "123", "bot_name": "Bot"}
    assert calls[0][1] == {"Authorization": "credential-placeholder"}


def test_validate_max_token_401_is_422(monkeypatch):
    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, headers): return httpx.Response(401)

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ChannelsService._validate_max_token("credential-placeholder"))
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Недействительный токен MAX"
    assert "credential-placeholder" not in exc_info.value.detail


def test_validate_max_token_timeout_is_controlled(monkeypatch):
    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, headers): raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(MaxTokenValidationUnavailableError) as exc_info:
        asyncio.run(ChannelsService._validate_max_token("credential-placeholder"))
    assert "credential-placeholder" not in str(exc_info.value)


class _Session:
    def add(self, obj):
        self.obj = obj
    async def commit(self):
        return None
    async def refresh(self, obj):
        return None


class _Channel:
    id = 7
    bot_id = 5
    channel_type = ChannelType.MAX
    is_active = True
    def __init__(self, config, is_active=True):
        self.config = config
        self.is_active = is_active


def test_update_max_token_preserves_webhook_secret_and_cleans_legacy(monkeypatch):
    from app.modules.channels import service as service_module
    from app.modules.channels.schemas import BotChannelUpdate

    async def validate(token):
        return {}
    async def sync(*args, **kwargs):
        return None

    monkeypatch.setattr(service_module, "decrypt_config", lambda value: value)
    monkeypatch.setattr(service_module, "encrypt_config", lambda value: value)
    monkeypatch.setattr(ChannelsService, "_validate_max_token", staticmethod(validate))
    monkeypatch.setattr(ChannelsService, "_sync_and_persist_max_webhook", sync)

    channel = _Channel({"token": "old", "webhook_secret": "stable", "webhook_status": "ok", "send_message_url": "legacy"})
    updated = asyncio.run(ChannelsService().update(_Session(), channel, BotChannelUpdate(config={"token": "new"})))

    assert updated.config["token"] == "new"
    assert updated.config["webhook_secret"] == "stable"
    assert "send_message_url" not in updated.config
    assert "secret" not in updated.config


def test_update_max_activation_without_token_returns_422(monkeypatch):
    from app.modules.channels import service as service_module
    from app.modules.channels.schemas import BotChannelUpdate

    monkeypatch.setattr(service_module, "decrypt_config", lambda value: value)
    monkeypatch.setattr(service_module, "encrypt_config", lambda value: value)

    channel = _Channel({"webhook_secret": "stable"}, is_active=False)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ChannelsService().update(_Session(), channel, BotChannelUpdate(is_active=True)))
    assert exc_info.value.status_code == 422


def test_sync_and_persist_max_webhook_keeps_disabled_status(monkeypatch):
    from app.modules.channels import service as service_module

    async def sync(channel, base_url):
        return "disabled", None

    monkeypatch.setattr(service_module, "sync_max_webhook", sync)
    monkeypatch.setattr(service_module, "_get_public_api_base_url", lambda: "https://example.com/api")
    monkeypatch.setattr(service_module, "encrypt_config", lambda value: value)

    channel = _Channel({"token": "old", "webhook_secret": "stable", "webhook_error": "old"}, is_active=False)
    asyncio.run(ChannelsService()._sync_and_persist_max_webhook(session=_Session(), db_obj=channel, decrypted=channel))

    assert channel.config["webhook_status"] == "disabled"
    assert "webhook_error" not in channel.config
