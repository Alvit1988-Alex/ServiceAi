import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import app.modules.channels.router as router_module
from app.modules.channels.models import ChannelType
from app.modules.channels.router import max_webhook


class _Channel:
    id = 7
    bot_id = 5
    channel_type = ChannelType.MAX
    def __init__(self, *, active=True, config=None):
        self.is_active = active
        self.config = config or {"webhook_secret": "expected-webhook-header", "token": "access-credential-placeholder"}


class _ChannelsService:
    def __init__(self, channel):
        self.channel = channel
    async def get(self, **kwargs):
        return self.channel
    def decrypt(self, channel):
        return channel


class _Diagnostics:
    async def log_integration(self, **kwargs):
        return None


def _request(headers=None):
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]})


def _payload(update_type="message_created"):
    if update_type != "message_created":
        return {"update_type": update_type}
    return {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 123},
            "recipient": {"chat_id": 456},
            "body": {"mid": "m1", "text": "hello"},
        },
    }


def test_max_webhook_accepts_valid_secret_and_processes(monkeypatch):
    processed = []

    async def process(**kwargs):
        processed.append(kwargs["normalized"])

    monkeypatch.setattr(router_module, "_process_and_broadcast", process)
    result = asyncio.run(max_webhook(
        bot_id=5,
        channel_id=7,
        payload=_payload(),
        request=_request({"X-Max-Bot-Api-Secret": "expected-webhook-header"}),
        session=None,
        channels_service=_ChannelsService(_Channel()),
        dialogs_service=None,
        ai_service=None,
        diagnostics_service=_Diagnostics(),
    ))

    assert result == {"status": "ok"}
    assert len(processed) == 1
    assert "headers" not in processed[0].payload


@pytest.mark.parametrize("headers", [{}, {"X-Max-Bot-Api-Secret": "wrong"}, {"Authorization": "access-credential-placeholder"}])
def test_max_webhook_rejects_missing_wrong_or_access_token_header(headers, monkeypatch):
    async def process(**kwargs):
        raise AssertionError("processing must not run")

    monkeypatch.setattr(router_module, "_process_and_broadcast", process)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(max_webhook(
            bot_id=5,
            channel_id=7,
            payload={**_payload(), "token": "access-credential-placeholder"},
            request=_request(headers),
            session=None,
            channels_service=_ChannelsService(_Channel()),
            dialogs_service=None,
            ai_service=None,
            diagnostics_service=_Diagnostics(),
        ))
    assert exc_info.value.status_code == 403


def test_max_webhook_unsupported_update_is_200_without_processing(monkeypatch):
    processed = []

    async def process(**kwargs):
        processed.append(kwargs)

    monkeypatch.setattr(router_module, "_process_and_broadcast", process)
    result = asyncio.run(max_webhook(
        bot_id=5,
        channel_id=7,
        payload=_payload("unsupported"),
        request=_request({"X-Max-Bot-Api-Secret": "expected-webhook-header"}),
        session=None,
        channels_service=_ChannelsService(_Channel()),
        dialogs_service=None,
        ai_service=None,
        diagnostics_service=_Diagnostics(),
    ))
    assert result == {"status": "ok"}
    assert processed == []


def test_max_webhook_disabled_channel_is_404():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(max_webhook(
            bot_id=5,
            channel_id=7,
            payload=_payload(),
            request=_request({"X-Max-Bot-Api-Secret": "expected-webhook-header"}),
            session=None,
            channels_service=_ChannelsService(_Channel(active=False)),
            dialogs_service=None,
            ai_service=None,
            diagnostics_service=_Diagnostics(),
        ))
    assert exc_info.value.status_code == 404
