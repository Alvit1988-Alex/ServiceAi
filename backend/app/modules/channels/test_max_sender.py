import asyncio
from types import SimpleNamespace

import httpx
import pytest

import app.modules.channels.sender_registry as sender_module
from app.modules.channels.sender_registry import ChannelSendError, MaxSender


class Diagnostics:
    def __init__(self):
        self.logs = []
    async def log_integration(self, **kwargs):
        self.logs.append(kwargs)


def _sender(channel, external_user_id="user-1"):
    sender = MaxSender()
    async def get_channel(bot_id):
        return channel
    async def resolve_user_id(bot_id, external_chat_id):
        return external_user_id
    sender._get_channel = get_channel
    sender._resolve_user_id = resolve_user_id
    return sender


def _channel(config=None):
    return SimpleNamespace(
        id=7,
        config=config if config is not None else {"token": "credential-placeholder"},
    )


def test_max_sender_group_chat_request_shape(monkeypatch):
    diagnostics = Diagnostics()
    calls = []
    monkeypatch.setattr(sender_module, "get_diagnostics_service", lambda: diagnostics)

    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, url, params, json, headers):
            calls.append((url, params, json, headers))
            return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    asyncio.run(_sender(_channel(), external_user_id="user-1").send_text(5, "chat-1", "Hello"))

    url, params, body, headers = calls[0]
    assert url == "https://platform-api2.max.ru/messages"
    assert params == {"chat_id": "chat-1"}
    assert body == {"text": "Hello"}
    assert headers["Authorization"] == "credential-placeholder"
    assert not headers["Authorization"].startswith("Bearer ")
    assert "chat_id" not in body and "message" not in body and "user_id" not in body
    assert diagnostics.logs[0]["status"] == "ok"


def test_max_sender_private_dialog_uses_user_id(monkeypatch):
    diagnostics = Diagnostics()
    calls = []
    monkeypatch.setattr(sender_module, "get_diagnostics_service", lambda: diagnostics)

    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, url, params, json, headers):
            calls.append((url, params, json, headers))
            return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    asyncio.run(_sender(_channel(), external_user_id="user-1").send_text(5, "user-1", "Hello"))

    assert calls[0][1] == {"user_id": "user-1"}
    assert calls[0][2] == {"text": "Hello"}


@pytest.mark.parametrize("status_code", [401, 500])
def test_max_sender_http_error_raises_and_logs_safe(monkeypatch, status_code):
    diagnostics = Diagnostics()
    monkeypatch.setattr(sender_module, "get_diagnostics_service", lambda: diagnostics)

    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, url, params, json, headers):
            return httpx.Response(status_code, text="provider-body", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(ChannelSendError):
        asyncio.run(_sender(_channel()).send_text(5, "chat-1", "Hello"))
    assert diagnostics.logs[0]["status"] == "fail"
    assert "provider-body" not in diagnostics.logs[0]["error_message"]
    assert "credential-placeholder" not in diagnostics.logs[0]["error_message"]


def test_max_sender_timeout_raises_and_logs_safe(monkeypatch):
    diagnostics = Diagnostics()
    monkeypatch.setattr(sender_module, "get_diagnostics_service", lambda: diagnostics)

    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, url, params, json, headers):
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(ChannelSendError):
        asyncio.run(_sender(_channel()).send_text(5, "chat-1", "Hello"))
    assert diagnostics.logs[0]["status"] == "fail"


def test_max_sender_missing_user_id_raises_without_guessing(monkeypatch):
    diagnostics = Diagnostics()
    monkeypatch.setattr(sender_module, "get_diagnostics_service", lambda: diagnostics)
    with pytest.raises(ChannelSendError):
        asyncio.run(_sender(_channel(), external_user_id=None).send_text(5, "chat-1", "Hello"))


def test_max_sender_missing_token_raises_without_http(monkeypatch):
    called = False
    class Client:
        def __init__(self, timeout):
            nonlocal called
            called = True

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(ChannelSendError, match="MAX token is not configured"):
        asyncio.run(_sender(_channel(config={})).send_text(5, "chat-1", "Hello"))
    assert called is False
