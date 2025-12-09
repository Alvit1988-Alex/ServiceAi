"""JWT utilities."""

from datetime import datetime, timedelta
from typing import Any, Dict

import jwt

# --- Python 3.10 fallback for StrEnum ---
try:
    from enum import StrEnum  # Python 3.11+
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        """Fallback for Python < 3.11."""
        pass
# ----------------------------------------

from app.config import settings


class TokenType(StrEnum):
    """Supported JWT token types."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenDecodeError(ValueError):
    """Raised when a token cannot be decoded or validated."""


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    if expires_minutes is None:
        expires_minutes = settings.access_token_expires_minutes
    return _create_token(
        subject=subject,
        secret_key=settings.jwt_secret_key,
        expires_delta=timedelta(minutes=expires_minutes),
        token_type=TokenType.ACCESS,
    )


def create_refresh_token(subject: str | int, expires_days: int | None = None) -> str:
    if expires_days is None:
        expires_days = settings.refresh_token_expires_days
    return _create_token(
        subject=subject,
        secret_key=settings.jwt_refresh_secret_key,
        expires_delta=timedelta(days=expires_days),
        token_type=TokenType.REFRESH,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    return _decode_token(
        token=token,
        secret_key=settings.jwt_secret_key,
        expected_type=TokenType.ACCESS,
    )


def decode_refresh_token(token: str) -> Dict[str, Any]:
    return _decode_token(
        token=token,
        secret_key=settings.jwt_refresh_secret_key,
        expected_type=TokenType.REFRESH,
    )


def _create_token(
    subject: str | int, secret_key: str, expires_delta: timedelta, token_type: TokenType
) -> str:
    now = datetime.utcnow()
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, secret_key, algorithm=settings.jwt_algorithm)


def _decode_token(token: str, secret_key: str, expected_type: TokenType) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:  # pragma: no cover
        raise TokenDecodeError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:  # pragma: no cover
        raise TokenDecodeError("Invalid token") from exc

    token_type = payload.get("type")
    if token_type != expected_type.value:
        raise TokenDecodeError("Token type mismatch")

    return payload
