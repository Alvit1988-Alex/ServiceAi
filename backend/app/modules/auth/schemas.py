"""Pydantic schemas for authentication endpoints."""
from datetime import datetime

from pydantic import BaseModel, EmailStr
from app.modules.auth.models import PendingLoginStatus


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
    exp: datetime | None = None
    type: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class LoginResponse(Token):
    pass


class PendingLoginResponse(BaseModel):
    token: str
    status: PendingLoginStatus
    expires_at: datetime
    telegram_deeplink: str


class PendingStatusResponse(BaseModel):
    status: PendingLoginStatus
    expires_at: datetime
    access_token: str | None = None
    refresh_token: str | None = None


class TelegramConfirmRequest(BaseModel):
    token: str
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class TelegramWebhookResponse(BaseModel):
    ok: bool
    message: str
