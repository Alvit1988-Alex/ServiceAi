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
            return httpx.Response(200, json={"user_id": 123, "name": "Bot"})

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    result = asyncio.run(ChannelsService._validate_max_token("token-value"))
    assert result == {"bot_id": "123", "bot_name": "Bot"}
    assert calls[0][1] == {"Authorization": "token-value"}


def test_validate_max_token_401_is_422(monkeypatch):
    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, headers): return httpx.Response(401)

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ChannelsService._validate_max_token("token-value"))
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Недействительный токен MAX"
    assert "token-value" not in exc_info.value.detail


def test_validate_max_token_timeout_is_controlled(monkeypatch):
    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, headers): raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(MaxTokenValidationUnavailableError) as exc_info:
        asyncio.run(ChannelsService._validate_max_token("token-value"))
    assert "token-value" not in str(exc_info.value)
