"""Utility functions for encrypting and decrypting channel configs."""

from __future__ import annotations

import hashlib
import json
from base64 import urlsafe_b64encode
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _get_cipher() -> Fernet:
    """Return a Fernet cipher instance using the configured secret key."""

    raw_key = settings.channel_config_secret_key
    if not raw_key:
        raise ValueError("channel_config_secret_key is not configured")

    key_bytes = raw_key.encode()
    if len(key_bytes) != 44:
        key_bytes = urlsafe_b64encode(hashlib.sha256(key_bytes).digest())

    return Fernet(key_bytes)


def encrypt_config(config: Dict[str, Any]) -> str:
    """
    Encrypt a channel configuration dictionary.

    The returned value is a URL-safe base64 string suitable for storage in JSON
    columns. If the input is falsy, it will be returned as-is.
    """

    if config is None:
        return config

    cipher = _get_cipher()
    serialized = json.dumps(config).encode()
    return cipher.encrypt(serialized).decode()


def decrypt_config(data: Any) -> Dict[str, Any]:
    """
    Decrypt a previously encrypted configuration value.

    If the input is already a dictionary, it is returned unchanged. Invalid
    tokens raise a ValueError.
    """

    if data is None:
        return data

    if isinstance(data, dict):
        return data

    if not isinstance(data, str):
        raise ValueError("Unsupported config payload for decryption")

    cipher = _get_cipher()
    try:
        decrypted = cipher.decrypt(data.encode())
    except InvalidToken as exc:  # pragma: no cover - safety check
        raise ValueError("Unable to decrypt channel configuration") from exc

    return json.loads(decrypted.decode())
