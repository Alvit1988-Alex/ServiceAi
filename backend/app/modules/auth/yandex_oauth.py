from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.accounts.models import User, UserRole
from app.modules.accounts.schemas import UserCreate
from app.modules.accounts.service import UsersService
from app.modules.auth.models import OAuthLoginSession, OAuthLoginSessionStatus

YANDEX_AUTH_URL = "https://oauth.yandex.ru/authorize"
YANDEX_TOKEN_URL = "https://oauth.yandex.ru/token"
YANDEX_USERINFO_URL = "https://login.yandex.ru/info"
YANDEX_OAUTH_SCOPE = "login:email login:info"
STATE_TTL = timedelta(minutes=5)
COMPLETION_TTL = timedelta(minutes=2)


class YandexOAuthError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(slots=True)
class YandexProfile:
    yandex_id: str
    email: str
    full_name: str | None
    first_name: str | None
    last_name: str | None
    username: str | None


class YandexOAuthService:
    provider = "yandex"

    def _now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def ensure_configured(self) -> None:
        if not (
            settings.yandex_oauth_client_id
            and settings.yandex_oauth_client_secret
            and settings.yandex_oauth_redirect_uri
            and settings.yandex_oauth_state_secret
            and settings.frontend_base_url
        ):
            raise YandexOAuthError("oauth_unavailable")

    def _build_login_url(self, **params: str) -> str:
        frontend_base = (settings.frontend_base_url or "").rstrip("/")
        if not frontend_base:
            raise YandexOAuthError("oauth_unavailable")
        query = urlencode(params)
        return f"{frontend_base}/login?{query}" if query else f"{frontend_base}/login"

    def build_error_redirect_url(self, error_code: str) -> str:
        return self._build_login_url(oauth_error=error_code)

    def build_success_redirect_url(self, completion_token: str) -> str:
        return self._build_login_url(oauth_token=completion_token)

    def _sign_state(self, payload: dict[str, Any]) -> str:
        secret = settings.yandex_oauth_state_secret.encode("utf-8")
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(secret, raw, hashlib.sha256).hexdigest()
        packed = {"payload": payload, "sig": signature}
        return base64.urlsafe_b64encode(json.dumps(packed, separators=(",", ":")).encode("utf-8")).decode("utf-8")

    def _verify_state(self, token: str) -> dict[str, Any]:
        try:
            raw = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
            packed = json.loads(raw)
            payload = packed["payload"]
            signature = packed["sig"]
        except Exception as exc:  # noqa: BLE001
            raise YandexOAuthError("invalid_state") from exc

        expected_signature = hmac.new(
            settings.yandex_oauth_state_secret.encode("utf-8"),
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise YandexOAuthError("invalid_state")

        issued_at = int(payload.get("ts", 0))
        if issued_at <= 0 or (time.time() - issued_at) > int(STATE_TTL.total_seconds()):
            raise YandexOAuthError("expired_state")

        nonce = payload.get("nonce")
        session_token = payload.get("state_token")
        if not nonce or len(str(nonce)) < 8 or not session_token:
            raise YandexOAuthError("invalid_state")

        return payload

    async def create_login_session(self, session: AsyncSession) -> str:
        self.ensure_configured()

        state_token = secrets.token_urlsafe(24)
        login_session = OAuthLoginSession(
            provider=self.provider,
            state_token=state_token,
            status=OAuthLoginSessionStatus.PENDING.value,
            expires_at=self._now() + STATE_TTL,
        )
        session.add(login_session)
        await session.commit()

        state = self._sign_state(
            {
                "state_token": state_token,
                "nonce": secrets.token_urlsafe(12),
                "ts": int(time.time()),
                "provider": self.provider,
            }
        )
        query = urlencode(
            {
                "response_type": "code",
                "client_id": settings.yandex_oauth_client_id,
                "redirect_uri": settings.yandex_oauth_redirect_uri,
                "scope": YANDEX_OAUTH_SCOPE,
                "state": state,
            }
        )
        return f"{YANDEX_AUTH_URL}?{query}"

    async def _lock_session_by_state_token(self, session: AsyncSession, state_token: str) -> OAuthLoginSession | None:
        result = await session.execute(
            select(OAuthLoginSession)
            .where(OAuthLoginSession.state_token == state_token)
            .with_for_update()
        )
        return result.scalars().first()

    async def _lock_session_by_completion_token(
        self,
        session: AsyncSession,
        completion_token: str,
    ) -> OAuthLoginSession | None:
        result = await session.execute(
            select(OAuthLoginSession)
            .where(OAuthLoginSession.completion_token == completion_token)
            .with_for_update()
        )
        return result.scalars().first()

    async def _exchange_code(self, code: str) -> str:
        payload = {
            "grant_type": "authorization_code",
            "client_id": settings.yandex_oauth_client_id,
            "client_secret": settings.yandex_oauth_client_secret,
            "code": code,
            "redirect_uri": settings.yandex_oauth_redirect_uri,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(YANDEX_TOKEN_URL, data=payload)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise YandexOAuthError("provider_unavailable") from exc

        if response.status_code >= 400:
            raise YandexOAuthError("token_exchange_failed")

        try:
            data = response.json()
        except ValueError as exc:
            raise YandexOAuthError("token_exchange_failed") from exc

        access_token = data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise YandexOAuthError("token_exchange_failed")
        return access_token

    async def _fetch_profile(self, access_token: str) -> YandexProfile:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    YANDEX_USERINFO_URL,
                    params={"format": "json"},
                    headers={"Authorization": f"OAuth {access_token}"},
                )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise YandexOAuthError("provider_unavailable") from exc

        if response.status_code >= 400:
            raise YandexOAuthError("profile_fetch_failed")

        try:
            data = response.json()
        except ValueError as exc:
            raise YandexOAuthError("profile_fetch_failed") from exc

        yandex_id = data.get("id")
        if not isinstance(yandex_id, str) or not yandex_id:
            raise YandexOAuthError("profile_fetch_failed")

        email = data.get("default_email")
        if not isinstance(email, str) or not email:
            emails = data.get("emails")
            if isinstance(emails, list):
                email = next((item for item in emails if isinstance(item, str) and item), None)
        if not isinstance(email, str) or not email:
            raise YandexOAuthError("email_required")

        first_name = data.get("first_name") if isinstance(data.get("first_name"), str) else None
        last_name = data.get("last_name") if isinstance(data.get("last_name"), str) else None
        display_name = data.get("display_name") if isinstance(data.get("display_name"), str) else None
        login = data.get("login") if isinstance(data.get("login"), str) else None
        full_name = " ".join(part for part in (first_name, last_name) if part) or display_name or None

        return YandexProfile(
            yandex_id=yandex_id,
            email=email.lower(),
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            username=login,
        )

    async def _get_user_by_yandex_id(self, session: AsyncSession, yandex_id: str) -> User | None:
        result = await session.execute(select(User).where(User.yandex_id == yandex_id))
        return result.scalars().first()

    async def _get_user_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).where(func.lower(User.email) == email.lower()))
        return result.scalars().first()

    async def _get_user_by_id(self, session: AsyncSession, user_id: int) -> User | None:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def _find_or_create_user(self, session: AsyncSession, profile: YandexProfile) -> User:
        user = await self._get_user_by_yandex_id(session=session, yandex_id=profile.yandex_id)
        if user:
            return user

        user = await self._get_user_by_email(session=session, email=profile.email)
        if user:
            if user.yandex_id and user.yandex_id != profile.yandex_id:
                raise YandexOAuthError("account_conflict")
            user.yandex_id = profile.yandex_id
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

        service = UsersService()
        user = await service.create(
            session=session,
            obj_in=UserCreate(
                email=profile.email,
                password=secrets.token_urlsafe(24),
                full_name=profile.full_name,
                telegram_id=None,
                username=profile.username,
                first_name=profile.first_name,
                last_name=profile.last_name,
                role=UserRole.owner,
                is_active=True,
                yandex_id=profile.yandex_id,
            ),
        )
        return user

    async def handle_callback(self, session: AsyncSession, *, code: str, state: str) -> str:
        self.ensure_configured()
        payload = self._verify_state(state)
        if payload.get("provider") != self.provider:
            raise YandexOAuthError("invalid_state")

        login_session = await self._lock_session_by_state_token(session=session, state_token=str(payload["state_token"]))
        if not login_session:
            raise YandexOAuthError("invalid_state")
        if login_session.provider != self.provider:
            raise YandexOAuthError("invalid_state")
        if login_session.status != OAuthLoginSessionStatus.PENDING.value:
            raise YandexOAuthError("invalid_state")
        if login_session.expires_at <= self._now():
            login_session.status = OAuthLoginSessionStatus.FAILED.value
            session.add(login_session)
            await session.commit()
            raise YandexOAuthError("expired_state")

        access_token = await self._exchange_code(code)
        profile = await self._fetch_profile(access_token)
        user = await self._find_or_create_user(session=session, profile=profile)

        login_session.user_id = user.id
        login_session.completion_token = secrets.token_urlsafe(24)
        login_session.status = OAuthLoginSessionStatus.COMPLETED.value
        login_session.expires_at = self._now() + COMPLETION_TTL
        session.add(login_session)
        await session.commit()
        return login_session.completion_token

    async def consume_completion_token(self, session: AsyncSession, completion_token: str) -> User:
        login_session = await self._lock_session_by_completion_token(
            session=session,
            completion_token=completion_token,
        )
        if not login_session:
            raise YandexOAuthError("invalid_completion_token")
        if login_session.provider != self.provider:
            raise YandexOAuthError("invalid_completion_token")
        if login_session.status != OAuthLoginSessionStatus.COMPLETED.value or not login_session.user_id:
            raise YandexOAuthError("invalid_completion_token")
        if login_session.consumed_at is not None:
            raise YandexOAuthError("completion_token_consumed")
        if login_session.expires_at <= self._now():
            login_session.status = OAuthLoginSessionStatus.FAILED.value
            session.add(login_session)
            await session.commit()
            raise YandexOAuthError("completion_token_expired")

        user = await self._get_user_by_id(session=session, user_id=login_session.user_id)
        if not user or not user.is_active:
            raise YandexOAuthError("user_unavailable")

        login_session.consumed_at = self._now()
        login_session.status = OAuthLoginSessionStatus.CONSUMED.value
        session.add(login_session)
        await session.commit()
        return user
