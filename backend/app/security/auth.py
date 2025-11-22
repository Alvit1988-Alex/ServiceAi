"""Authentication placeholder utilities."""

from datetime import datetime, timedelta

from app.config import settings


def create_access_token(subject: str) -> dict:
    expires = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return {"sub": subject, "exp": expires.timestamp()}
