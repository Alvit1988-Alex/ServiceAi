from app.modules.channels.max_handler import normalize_max_webhook
from app.modules.channels.schemas import ChannelType


def _message_payload(**overrides):
    payload = {
        "update_type": "message_created",
        "timestamp": 1720000000000,
        "message": {
            "sender": {"user_id": 123456789, "name": "User"},
            "recipient": {"chat_id": 987654321, "user_id": 123456789, "chat_type": "dialog"},
            "body": {"mid": "message-id", "seq": 1, "text": "Привет"},
        },
    }
    for key, value in overrides.items():
        payload["message"][key] = value
    return payload


def test_message_created_with_chat_id_normalized_without_headers():
    normalized = normalize_max_webhook(1, 2, _message_payload())

    assert normalized is not None
    assert normalized.external_user_id == "123456789"
    assert normalized.external_chat_id == "987654321"
    assert normalized.external_message_id == "message-id"
    assert normalized.text == "Привет"
    assert normalized.channel_type == ChannelType.MAX
    assert "headers" not in normalized.payload


def test_message_created_uses_recipient_user_id_when_chat_id_missing():
    payload = _message_payload(recipient={"user_id": 222})

    normalized = normalize_max_webhook(1, 2, payload)

    assert normalized is not None
    assert normalized.external_chat_id == "222"


def test_message_created_missing_sender_user_id_returns_none():
    assert normalize_max_webhook(1, 2, _message_payload(sender={})) is None


def test_message_created_missing_recipient_ids_returns_none():
    assert normalize_max_webhook(1, 2, _message_payload(recipient={})) is None


def test_message_created_empty_text_returns_none():
    assert normalize_max_webhook(1, 2, _message_payload(body={"mid": "1", "text": "  "})) is None


def test_unsupported_update_type_returns_none():
    assert normalize_max_webhook(1, 2, {"update_type": "unknown"}) is None


def test_bot_started_without_payload_returns_none():
    assert normalize_max_webhook(1, 2, {"update_type": "bot_started", "user": {"user_id": 1}}) is None


def test_malformed_payloads_do_not_raise():
    assert normalize_max_webhook(1, 2, {"update_type": "message_created", "message": None}) is None
    assert normalize_max_webhook(1, 2, None) is None
