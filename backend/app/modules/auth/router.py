"""Authentication API router."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import re
import secrets
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db_session
from app.modules.accounts.models import User, UserRole
from app.modules.accounts.schemas import UserCreate, UserOut
from app.modules.accounts.service import AccountsService, UsersService
from app.modules.auth.models import PendingLogin, PendingLoginStatus
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    PendingLoginResponse,
    PendingStatusResponse,
    RefreshRequest,
    Token,
    TelegramConfirmRequest,
    TelegramWebhookResponse,
)
from app.security import hashing
from app.security.auth import get_current_user
from app.security.jwt import (
    TokenDecodeError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
MAX_AVATAR_SIZE = 2 * 1024 * 1024
_CACHED_TG_USERNAME: str | None = None


def _now() -> datetime:
    return datetime.utcnow()


def _normalize_telegram_email_username(raw_value: str, telegram_id: int) -> str:
    normalized = raw_value.strip().lower()
    normalized = re.sub(r"[^a-z0-9_.-]+", "_", normalized)
    normalized = normalized.strip("_")
    if not normalized:
        normalized = str(telegram_id)
    return normalized


def _telegram_webhook_path() -> str:
    path = settings.telegram_webhook_path or "/auth/telegram/webhook"
    if path.startswith("/auth"):
        path = path[len("/auth") :]
        if not path:
            path = "/"
    if not path.startswith("/"):
        path = f"/{path}"
    return path


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def _get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def _get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()


async def _get_pending_by_token(session: AsyncSession, token: str) -> PendingLogin | None:
    result = await session.execute(select(PendingLogin).where(PendingLogin.token == token))
    return result.scalars().first()


async def _lock_pending_by_id(session: AsyncSession, pending_id: int) -> PendingLogin | None:
    result = await session.execute(
        select(PendingLogin).where(PendingLogin.id == pending_id).with_for_update()
    )
    return result.scalars().first()


def _ensure_password_enabled() -> None:
    if settings.auth_telegram_only:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Password login is disabled",
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> Token:
    _ensure_password_enabled()

    user = await _get_user_by_email(session=session, email=data.email)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if not hashing.verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    data: RefreshRequest, session: AsyncSession = Depends(get_db_session)
) -> Token:
    try:
        payload = decode_refresh_token(data.refresh_token)
        user_id = payload.get("sub")
        if user_id is None:
            raise TokenDecodeError("Invalid token payload")
    except TokenDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from exc

    user = await _get_user_by_id(session=session, user_id=int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return current_user


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserOut:
    if file.content_type != "image/webp":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image/webp is supported",
        )

    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar file is too large",
        )

    avatar_dir = Path(settings.webchat_static_dir) / "avatars" / f"u_{current_user.id}"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    avatar_path = avatar_dir / "avatar.webp"

    avatar_path.write_bytes(content)

    current_user.avatar_url = f"/static/avatars/u_{current_user.id}/avatar.webp"
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return current_user


@router.delete("/me/avatar", response_model=UserOut)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserOut:
    avatar_dir = Path(settings.webchat_static_dir) / "avatars" / f"u_{current_user.id}"
    avatar_path = avatar_dir / "avatar.webp"
    if avatar_path.exists():
        avatar_path.unlink()

    current_user.avatar_url = None
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return current_user


@router.post("/change-password", response_model=UserOut)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserOut:
    if settings.auth_telegram_only:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password changes are disabled",
        )

    user = await _get_user_by_id(session=session, user_id=current_user.id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not hashing.verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
        )

    user.password_hash = hashing.hash_password(data.new_password)
    await session.commit()
    await session.refresh(user)
    return user


async def _resolve_bot_username() -> str | None:
    if settings.telegram_auth_bot_username:
        return settings.telegram_auth_bot_username

    global _CACHED_TG_USERNAME
    if _CACHED_TG_USERNAME:
        return _CACHED_TG_USERNAME

    if not settings.telegram_auth_bot_token:
        return None

    bot_base_url = f"https://api.telegram.org/bot{settings.telegram_auth_bot_token}"
    try:
        async with httpx.AsyncClient(base_url=bot_base_url, timeout=3) as client:
            response = await client.get("/getMe")
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return None

    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, dict):
            username = result.get("username")
            if isinstance(username, str) and username:
                _CACHED_TG_USERNAME = username
                return username

    return None


async def _build_deeplink(token: str) -> str:
    username = await _resolve_bot_username()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telegram bot username is not configured and cannot be resolved via token",
        )
    return f"https://t.me/{username}?start=login_{token}"


def _expires_at() -> datetime:
    return _now() + timedelta(minutes=5)


def _mask_bot_token(token: str | None) -> str:
    if not token:
        return ""
    if len(token) <= 6:
        return "*" * len(token)
    return f"{token[:3]}***{token[-3:]}"


async def _mark_expired(pending: PendingLogin, session: AsyncSession) -> PendingLogin:
    pending.status = PendingLoginStatus.EXPIRED.value
    session.add(pending)
    await session.commit()
    await session.refresh(pending)
    return pending


async def _create_pending_login(request: Request, session: AsyncSession) -> PendingLogin:
    token = secrets.token_urlsafe(24)
    expires_at = _expires_at()
    pending = PendingLogin(
        token=token,
        status=PendingLoginStatus.PENDING.value,
        expires_at=expires_at,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(pending)
    await session.commit()
    await session.refresh(pending)
    return pending


async def _ensure_pending_valid(pending: PendingLogin, session: AsyncSession) -> PendingLogin:
    if pending.status == PendingLoginStatus.PENDING.value and pending.expires_at <= _now():
        pending = await _mark_expired(pending, session)
    if pending.status == PendingLoginStatus.EXPIRED.value:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Pending login expired")
    if pending.status == PendingLoginStatus.CONFIRMED.value:
        return pending
    return pending


async def _find_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
) -> User:
    existing = await _get_user_by_telegram_id(session=session, telegram_id=telegram_id)
    if existing:
        return existing

    email_username = _normalize_telegram_email_username(username or str(telegram_id), telegram_id)
    # .local is reserved/special-use and rejected by email validators.
    email = f"{email_username}@telegram-login.example.com"
    password = secrets.token_urlsafe(16)
    full_name_parts = [part for part in (first_name, last_name) if part]
    full_name = " ".join(full_name_parts) if full_name_parts else None

    service = UsersService()
    user = await service.create(
        session=session,
        obj_in=UserCreate(
            email=email,
            password=password,
            full_name=full_name,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.owner,
            is_active=True,
        ),
    )

    # Ensure default account exists
    accounts_service = AccountsService()
    await accounts_service.get_or_create_for_owner(session=session, owner=user)

    return user


async def _confirm_pending(
    session: AsyncSession,
    payload: TelegramConfirmRequest,
) -> PendingLogin:
    pending = await _get_pending_by_token(session=session, token=payload.token)
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending login not found")

    await _ensure_pending_valid(pending, session)
    if pending.status == PendingLoginStatus.CONFIRMED.value:
        return pending

    user = await _find_or_create_user(
        session=session,
        telegram_id=payload.telegram_id,
        username=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )

    pending.telegram_id = payload.telegram_id
    pending.user_id = user.id
    pending.status = PendingLoginStatus.CONFIRMED.value
    session.add(pending)
    await session.commit()
    await session.refresh(pending)
    return pending


async def _send_telegram_confirmation_message(chat_id: int | str, text: str) -> None:
    if not settings.telegram_auth_bot_token:
        return

    bot_base_url = f"https://api.telegram.org/bot{settings.telegram_auth_bot_token}"
    try:
        async with httpx.AsyncClient(base_url=bot_base_url, timeout=3) as client:
            await client.post(
                "/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                },
            )
    except Exception:
        if settings.runtime_debug:
            # pragma: no cover - diagnostic logging only in debug
            masked_token = _mask_bot_token(settings.telegram_auth_bot_token)
            print(  # noqa: T201
                f"Failed to send Telegram confirmation using bot={masked_token}"
            )


async def _consume_pending_login(session: AsyncSession, pending: PendingLogin) -> tuple[PendingLogin, bool]:
    if pending.status != PendingLoginStatus.CONFIRMED.value or not pending.user_id:
        return pending, False

    locked_pending = await _lock_pending_by_id(session=session, pending_id=pending.id)
    if locked_pending is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending login not found")

    if locked_pending.consumed_at is None:
        locked_pending.consumed_at = _now()
        session.add(locked_pending)
        await session.commit()
        await session.refresh(locked_pending)
        return locked_pending, True

    await session.refresh(locked_pending)
    return locked_pending, False


@router.post("/pending", response_model=PendingLoginResponse)
async def create_pending_login(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> PendingLoginResponse:
    pending = await _create_pending_login(request=request, session=session)
    return PendingLoginResponse(
        token=pending.token,
        status=pending.status,
        expires_at=pending.expires_at,
        telegram_deeplink=await _build_deeplink(pending.token),
    )


@router.get("/pending/{token}/status", response_model=PendingStatusResponse)
async def get_pending_status(
    token: str,
    session: AsyncSession = Depends(get_db_session),
) -> PendingStatusResponse:
    pending = await _get_pending_by_token(session=session, token=token)
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending login not found")

    pending = await _ensure_pending_valid(pending, session)

    access_token = None
    refresh_token = None
    if pending.status == PendingLoginStatus.CONFIRMED.value and pending.user_id:
        pending, should_issue_tokens = await _consume_pending_login(session=session, pending=pending)
        if should_issue_tokens:
            access_token = create_access_token(subject=pending.user_id)
            refresh_token = create_refresh_token(subject=pending.user_id)

    return PendingStatusResponse(
        status=pending.status,
        expires_at=pending.expires_at,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/telegram/confirm", response_model=PendingStatusResponse)
async def confirm_telegram_login(
    payload: TelegramConfirmRequest,
    session: AsyncSession = Depends(get_db_session),
) -> PendingStatusResponse:
    pending = await _confirm_pending(session=session, payload=payload)

    access_token = None
    refresh_token = None
    if pending.user_id:
        pending, should_issue_tokens = await _consume_pending_login(session=session, pending=pending)
        if should_issue_tokens:
            access_token = create_access_token(subject=pending.user_id)
            refresh_token = create_refresh_token(subject=pending.user_id)

    return PendingStatusResponse(
        status=pending.status,
        expires_at=pending.expires_at,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(_telegram_webhook_path(), response_model=TelegramWebhookResponse)
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> TelegramWebhookResponse:
    secret = request.query_params.get("secret")
    if not secret:
        # Telegram sends the secret token in the official header.
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token") or request.headers.get(
            "X-Telegram-Secret"
        )
    if not settings.telegram_webhook_secret or secret != settings.telegram_webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")

    if not settings.telegram_auth_bot_token:
        # Avoid 500 responses for Telegram retries; just log in debug.
        if settings.runtime_debug:
            # pragma: no cover - diagnostic logging only in debug
            print("Telegram bot token is not configured")  # noqa: T201
        return TelegramWebhookResponse(ok=True, message="Bot token is not configured")

    try:
        payload = await request.json()
    except Exception:
        # Telegram should receive 200 even if payload is invalid.
        if settings.runtime_debug:
            # pragma: no cover - diagnostic logging only in debug
            print("Invalid Telegram webhook payload")  # noqa: T201
        return TelegramWebhookResponse(ok=True, message="Invalid payload")
    message = payload.get("message") or {}
    text = message.get("text") or ""
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}

    start_param: str | None = None
    token: str | None = None
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0] if parts else ""
    if len(parts) > 1:
        start_param = parts[1].strip()

    if start_param and start_param.startswith("login_"):
        token = start_param[len("login_") :].strip()

    if settings.runtime_debug:
        # pragma: no cover - diagnostic logging only in debug
        print("Telegram webhook text:", repr(text))  # noqa: T201
        print("Parsed start_param:", repr(start_param))  # noqa: T201
        print("Parsed token:", repr(token))  # noqa: T201

    if not cmd.startswith("/start"):
        if settings.runtime_debug:
            # pragma: no cover - diagnostic logging only in debug
            print("Result: ignored")  # noqa: T201
        return TelegramWebhookResponse(ok=True, message="Ignored non-start message")

    if not start_param or not start_param.startswith("login_"):
        info_text = (
            "⚠️ Для входа откройте ссылку авторизации на сайте и нажмите «Открыть в Telegram» ещё раз. "
            "Важно: команда должна прийти как /start login_<token>."
        )
        chat_id = chat.get("id") or from_user.get("id")
        if chat_id:
            background_tasks.add_task(_send_telegram_confirmation_message, chat_id, info_text)
        if settings.runtime_debug:
            # pragma: no cover - diagnostic logging only in debug
            print("Result: missing token")  # noqa: T201
        return TelegramWebhookResponse(ok=True, message="Start message handled")

    if not from_user.get("id"):
        if settings.runtime_debug:
            # pragma: no cover - diagnostic logging only in debug
            print("Missing Telegram user identifier")  # noqa: T201
        return TelegramWebhookResponse(ok=True, message="Missing Telegram user identifier")

    if not token:
        expired_text = (
            "Ссылка для входа устарела. Вернитесь на сайт и нажмите “Войти через Telegram” ещё раз."
        )
        chat_id = chat.get("id") or from_user.get("id")
        if chat_id:
            background_tasks.add_task(_send_telegram_confirmation_message, chat_id, expired_text)
        if settings.runtime_debug:
            # pragma: no cover - diagnostic logging only in debug
            print("Result: missing token")  # noqa: T201
        return TelegramWebhookResponse(ok=True, message="Login token missing")
    confirm_payload = TelegramConfirmRequest(
        token=token,
        telegram_id=int(from_user.get("id")),
        username=from_user.get("username"),
        first_name=from_user.get("first_name"),
        last_name=from_user.get("last_name"),
    )

    try:
        pending = await _confirm_pending(session=session, payload=confirm_payload)
    except HTTPException:
        expired_text = (
            "Ссылка для входа устарела. Вернитесь на сайт и нажмите “Войти через Telegram” ещё раз."
        )
        chat_id = chat.get("id") or from_user.get("id")
        if chat_id:
            background_tasks.add_task(_send_telegram_confirmation_message, chat_id, expired_text)
        if settings.runtime_debug:
            # pragma: no cover - diagnostic logging only in debug
            print("Result: ignored")  # noqa: T201
        return TelegramWebhookResponse(ok=True, message="Login token invalid")

    reply_text = "✅ Вход подтвержден. Вернитесь в браузер, чтобы продолжить."
    chat_id = chat.get("id") or from_user.get("id")
    background_tasks.add_task(_send_telegram_confirmation_message, chat_id, reply_text)

    masked_token = _mask_bot_token(settings.telegram_auth_bot_token)
    masked_secret = _mask_bot_token(settings.telegram_webhook_secret)
    # Minimal logging for observability without exposing secrets
    if settings.runtime_debug:
        # pragma: no cover - diagnostic logging only in debug
        print("Result: consumed")  # noqa: T201
        print(  # noqa: T201
            f"Telegram webhook processed for token={token[:4]}*** using bot={masked_token} secret={masked_secret}"
        )

    return TelegramWebhookResponse(ok=True, message="Login confirmed")
