import asyncio

import httpx

from app.modules.channels.max_webhook import MAX_SUBSCRIPTIONS_URL, build_max_webhook_url, sync_max_webhook
from app.modules.channels.models import BotChannel, ChannelType


def _channel(active=True):
    return BotChannel(
        id=7,
        bot_id=5,
        channel_type=ChannelType.MAX,
        is_active=active,
        config={"token": "credential-placeholder", "webhook_secret": "webhook-credential-placeholder"},
    )


def test_build_max_webhook_url_uses_existing_route():
    assert build_max_webhook_url(_channel(), "https://example.com/api") == "https://example.com/api/bots/5/channels/webhooks/max/7"


def test_sync_active_channel_creates_subscription(monkeypatch):
    calls = []

    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, headers):
            calls.append(("GET", url, None, None, headers))
            return httpx.Response(200, json={"subscriptions": []}, request=httpx.Request("GET", url))
        async def post(self, url, json, headers):
            calls.append(("POST", url, None, json, headers))
            return httpx.Response(200, json={"success": True}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    status, error = asyncio.run(sync_max_webhook(_channel(), "https://example.com/api"))

    assert (status, error) == ("ok", None)
    post = calls[1]
    assert post[1] == MAX_SUBSCRIPTIONS_URL
    assert post[3]["url"] == "https://example.com/api/bots/5/channels/webhooks/max/7"
    assert set(post[3]["update_types"]) == {"message_created", "bot_started"}
    assert post[3]["secret"] == "webhook-credential-placeholder"
    assert post[4]["Authorization"] == "credential-placeholder"


def test_sync_existing_subscription_updates_with_post(monkeypatch):
    calls = []

    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, headers):
            calls.append(("GET", url))
            return httpx.Response(200, json={"subscriptions": [{"url": "https://example.com/api/bots/5/channels/webhooks/max/7"}]}, request=httpx.Request("GET", url))
        async def post(self, url, json, headers):
            calls.append(("POST", url, json, headers))
            return httpx.Response(200, json={"success": True}, request=httpx.Request("POST", url))
        async def delete(self, *args, **kwargs):
            calls.append(("DELETE", args, kwargs))
            return httpx.Response(200, json={"success": True}, request=httpx.Request("DELETE", args[0]))

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    status, error = asyncio.run(sync_max_webhook(_channel(), "https://example.com/api"))
    assert (status, error) == ("ok", None)
    assert [call[0] for call in calls] == ["GET", "POST"]
    assert calls[1][2]["update_types"] == ["message_created", "bot_started"]
    assert calls[1][2]["secret"] == "webhook-credential-placeholder"


def test_sync_disabled_deletes_current_url_only(monkeypatch):
    calls = []

    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, headers):
            return httpx.Response(200, json={"subscriptions": [
                {"id": "own", "url": "https://example.com/api/bots/5/channels/webhooks/max/7"},
                {"id": "other", "url": "https://example.com/api/other"},
            ]}, request=httpx.Request("GET", url))
        async def delete(self, url, headers, params=None):
            calls.append((url, params))
            return httpx.Response(200, json={"success": True}, request=httpx.Request("DELETE", url))

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    status, error = asyncio.run(sync_max_webhook(_channel(active=False), "https://example.com/api"))
    assert (status, error) == ("disabled", None)
    assert calls == [(MAX_SUBSCRIPTIONS_URL, {"url": "https://example.com/api/bots/5/channels/webhooks/max/7"})]


def test_sync_without_public_base_url_is_pending(monkeypatch):
    status, error = asyncio.run(sync_max_webhook(_channel(), None))
    assert status == "pending"
    assert error == "Public base URL is not configured"


def test_sync_provider_error_is_safe(monkeypatch):
    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, headers): return httpx.Response(401, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    status, error = asyncio.run(sync_max_webhook(_channel(), "https://example.com/api"))
    assert status == "error"
    assert error == "MAX subscriptions API error: HTTP 401"
    assert "credential-placeholder" not in error


def test_sync_post_success_false_is_error(monkeypatch):
    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, headers):
            return httpx.Response(200, json={"subscriptions": []}, request=httpx.Request("GET", url))
        async def post(self, url, json, headers):
            return httpx.Response(
                200,
                json={
                    "success": False,
                    "message": "Rejected credential-placeholder and webhook-credential-placeholder",
                },
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    status, error = asyncio.run(sync_max_webhook(_channel(), "https://example.com/api"))
    assert status == "error"
    assert error == "Rejected [REDACTED] and [REDACTED]"
    assert "credential-placeholder" not in error
    assert "webhook-credential-placeholder" not in error
    assert "[REDACTED]" in error


def test_sync_delete_success_false_is_error(monkeypatch):
    class Client:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, headers):
            return httpx.Response(200, json={"subscriptions": [{"url": "https://example.com/api/bots/5/channels/webhooks/max/7"}]}, request=httpx.Request("GET", url))
        async def delete(self, url, headers, params=None):
            return httpx.Response(
                200,
                json={
                    "success": False,
                    "message": "Delete rejected credential-placeholder and webhook-credential-placeholder",
                },
                request=httpx.Request("DELETE", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    status, error = asyncio.run(sync_max_webhook(_channel(active=False), "https://example.com/api"))
    assert status == "error"
    assert error == "Delete rejected [REDACTED] and [REDACTED]"
    assert "credential-placeholder" not in error
    assert "webhook-credential-placeholder" not in error
    assert "[REDACTED]" in error
