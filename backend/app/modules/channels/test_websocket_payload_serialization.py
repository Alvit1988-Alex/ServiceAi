"""Regression tests for WebSocket payload JSON serialization."""

import asyncio
import json
from datetime import datetime
from types import SimpleNamespace

from app.modules.channels.models import ChannelType
from app.modules.channels import router as channels_router
from app.modules.dialogs import router as dialogs_router
from app.modules.dialogs.models import DialogStatus, MessageSender


def _dialog(*, messages=None):
    now = datetime(2026, 7, 24, 12, 30, 45)
    return SimpleNamespace(
        id=10,
        bot_id=3,
        channel_type=ChannelType.MAX,
        external_chat_id="chat-14",
        external_user_id="user-14",
        status=DialogStatus.AUTO,
        closed=False,
        last_message_at=now,
        last_user_message_at=now,
        unread_messages_count=1,
        is_locked=True,
        locked_until=now,
        assigned_admin_id=7,
        assigned_admin=None,
        waiting_time_seconds=5,
        created_at=now,
        updated_at=now,
        messages=messages or [],
    )


def _message():
    now = datetime(2026, 7, 24, 12, 31, 45)
    return SimpleNamespace(
        id=20,
        dialog_id=10,
        sender=MessageSender.USER,
        text="hello",
        payload={"source": "max"},
        operator_admin_id=None,
        operator_admin=None,
        created_at=now,
        updated_at=now,
    )


def _assert_json_payload(payload):
    json.dumps(payload)
    assert isinstance(payload["created_at"], str)
    assert isinstance(payload["updated_at"], str)


def test_channel_broadcast_message_events_payloads_are_json_serializable(monkeypatch):
    captured = []

    async def broadcast_to_admins(message, admin_ids=None):
        captured.append(message)

    async def broadcast_to_webchat(*, bot_id, session_id, message):
        captured.append(message)

    monkeypatch.setattr(channels_router.manager, "broadcast_to_admins", broadcast_to_admins)
    monkeypatch.setattr(channels_router.manager, "broadcast_to_webchat", broadcast_to_webchat)

    message = _message()
    dialog = _dialog(messages=[message])

    asyncio.run(channels_router._broadcast_message_events([message], dialog, dialog_created=True))

    assert {event["event"] for event in captured} == {"dialog_created", "message_created", "dialog_updated"}
    for event in captured:
        json.dumps(event)
        _assert_json_payload(event["data"])


def test_dialog_detail_websocket_payload_is_json_serializable():
    payload = dialogs_router._build_dialog_detail(_dialog(messages=[_message()])).model_dump(mode="json")

    json.dumps(payload)
    _assert_json_payload(payload)
    _assert_json_payload(payload["messages"][0])
