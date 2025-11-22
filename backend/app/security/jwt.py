"""JWT utilities."""

from datetime import datetime, timedelta
from typing import Any, Dict

import jwt

from app.config import settings


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    if expires_minutes is None:
        expires_minutes = settings.access_token_expires_minutes
    return _create_token(
        subject=subject,
        secret_key=settings.jwt_secret_key,
        expires_delta=timedelta(minutes=expires_minutes),
    )


def create_refresh_token(subject: str | int, expires_days: int | None = None) -> str:
    if expires_days is None:
        expires_days = settings.refresh_token_expires_days
    return _create_token(
        subject=subject,
        secret_key=settings.jwt_refresh_secret_key,
        expires_delta=timedelta(days=expires_days),
    )


def _create_token(subject: str | int, secret_key: str, expires_delta: timedelta) -> str:
    now = datetime.utcnow()
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, secret_key: str) -> Dict[str, Any]:
    """Lightweight token decoder placeholder."""

    return jwt.decode(token, secret_key, algorithms=[settings.jwt_algorithm])
