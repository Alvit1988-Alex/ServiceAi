from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.modules.dialogs.models import Dialog
from app.modules.integrations.bitrix24.models import BitrixDialogLink, BitrixIntegration

logger = logging.getLogger(__name__)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class BitrixIntegrationError(Exception):
    pass


class BitrixRateLimitError(BitrixIntegrationError):
    pass


class Bitrix24Service:
    CONNECTOR_ID = "serviceai"
    CONNECTOR_NAME = "ServiceAI"
    connector_name = CONNECTOR_ID
    _registered_cache: set[tuple[str, str]] = set()

    def normalize_portal_url(self, portal_domain: str) -> str:
        cleaned = portal_domain.strip().lower()
        if not cleaned:
            raise BitrixIntegrationError("Неверный адрес Bitrix24")

        if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
            cleaned = f"https://{cleaned}"

        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise BitrixIntegrationError("Неверный адрес Bitrix24")

        domain = parsed.netloc.strip().lower()
        if "." not in domain:
            raise BitrixIntegrationError("Неверный адрес Bitrix24")

        return f"https://{domain}"

    def _sign_state(self, payload: dict[str, Any]) -> str:
        if not settings.bitrix24_connect_state_secret:
            raise BitrixIntegrationError("Bitrix24 OAuth не настроен")
        secret = settings.bitrix24_connect_state_secret.encode("utf-8")
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(secret, raw, hashlib.sha256).hexdigest()
        packed = {"payload": payload, "sig": signature}
        token = base64.urlsafe_b64encode(json.dumps(packed, separators=(",", ":")).encode("utf-8")).decode("utf-8")
        return token

    def _verify_state(self, token: str) -> dict[str, Any]:
        try:
            raw = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
            packed = json.loads(raw)
            payload = packed["payload"]
            signature = packed["sig"]
        except Exception as exc:  # noqa: BLE001
            raise BitrixIntegrationError("Неверный state OAuth") from exc

        expected_sig = hmac.new(
            settings.bitrix24_connect_state_secret.encode("utf-8"),
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            raise BitrixIntegrationError("Неверный state OAuth")

        issued_at = int(payload.get("ts", 0))
        if issued_at <= 0 or (time.time() - issued_at) > 900:
            raise BitrixIntegrationError("Срок действия подключения истек")

        nonce = payload.get("nonce")
        if not nonce or len(str(nonce)) < 8:
            raise BitrixIntegrationError("Неверный state OAuth")

        return payload

    def build_auth_url(self, *, bot_id: int, portal_url: str) -> str:
        scopes = settings.bitrix24_app_scopes
        payload = {
            "bot_id": bot_id,
            "portal_url": portal_url,
            "nonce": secrets.token_urlsafe(12),
            "ts": int(time.time()),
        }
        state = self._sign_state(payload)
        query = urlencode(
            {
                "client_id": settings.bitrix24_app_client_id,
                "response_type": "code",
                "redirect_uri": settings.bitrix24_app_redirect_url,
                "scope": scopes,
                "state": state,
            }
        )
        return f"{portal_url}/oauth/authorize/?{query}"

    async def exchange_code(self, *, code: str, portal_url: str) -> dict[str, Any]:
        token_url = settings.bitrix24_oauth_token_url or f"{portal_url}/oauth/token/"
        payload = {
            "grant_type": "authorization_code",
            "client_id": settings.bitrix24_app_client_id,
            "client_secret": settings.bitrix24_app_client_secret,
            "code": code,
            "redirect_uri": settings.bitrix24_app_redirect_url,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(token_url, data=payload)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise BitrixIntegrationError("Ошибка соединения с Bitrix24") from exc

        if response.status_code >= 400:
            logger.error("Bitrix token exchange failed", extra={"status_code": response.status_code})
            raise BitrixIntegrationError("Нет прав доступа (scope)")

        try:
            data = response.json()
        except ValueError as exc:
            raise BitrixIntegrationError("Не удалось получить токен Bitrix24") from exc

        if data.get("error"):
            raise BitrixIntegrationError("Нет прав доступа (scope)")

        return data

    async def refresh_access_token(self, session: AsyncSession, integration: BitrixIntegration) -> BitrixIntegration:
        token_url = settings.bitrix24_oauth_token_url or f"{integration.portal_url}/oauth/token/"

        if not integration.refresh_token:
            raise BitrixIntegrationError("Отсутствует refresh_token")

        payload = {
            "grant_type": "refresh_token",
            "client_id": settings.bitrix24_app_client_id,
            "client_secret": settings.bitrix24_app_client_secret,
            "refresh_token": integration.refresh_token,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(token_url, data=payload)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise BitrixIntegrationError("Ошибка соединения с Bitrix24") from exc

        if response.status_code >= 400:
            logger.error(
                "Bitrix token refresh failed",
                extra={"status_code": response.status_code, "bot_id": integration.bot_id},
            )
            raise BitrixIntegrationError("Не удалось обновить токен")

        try:
            data = response.json()
        except ValueError as exc:
            raise BitrixIntegrationError("Не удалось обновить токен") from exc

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        if not access_token or not refresh_token:
            raise BitrixIntegrationError("Не удалось обновить токен")

        integration.access_token = access_token
        integration.refresh_token = refresh_token
        expires_in = int(data.get("expires_in", 3600))
        integration.expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=expires_in - 30)
        integration.scope = data.get("scope") or integration.scope
        integration.member_id = data.get("member_id") or integration.member_id
        integration.enabled = True

        session.add(integration)
        await session.commit()
        await session.refresh(integration)
        return integration

    async def get_integration(self, session: AsyncSession, bot_id: int) -> BitrixIntegration | None:
        result = await session.execute(select(BitrixIntegration).where(BitrixIntegration.bot_id == bot_id))
        return result.scalars().first()

    async def ensure_active_integration(self, session: AsyncSession, bot_id: int) -> BitrixIntegration | None:
        integration = await self.get_integration(session=session, bot_id=bot_id)
        if not integration or not integration.enabled:
            return None

        if integration.expires_at and integration.expires_at <= utcnow_naive():
            integration = await self.refresh_access_token(session=session, integration=integration)
        return integration

    async def call_rest(
        self,
        *,
        session: AsyncSession,
        integration: BitrixIntegration,
        method_name: str,
        params: dict[str, Any],
        max_retries: int = 3,
    ) -> dict[str, Any]:
        active_integration = integration
        if active_integration.expires_at and active_integration.expires_at <= utcnow_naive():
            active_integration = await self.refresh_access_token(session=session, integration=active_integration)

        endpoint = f"{active_integration.portal_url}/rest/{method_name}.json"
        payload = {**params, "auth": active_integration.access_token}

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(endpoint, json=payload)

                if response.status_code == 401 and attempt == 1:
                    active_integration = await self.refresh_access_token(session=session, integration=active_integration)
                    payload["auth"] = active_integration.access_token
                    continue

                if response.status_code == 429:
                    if attempt == max_retries:
                        raise BitrixRateLimitError("Превышен лимит Bitrix24 REST")
                    await self._backoff(attempt)
                    continue

                try:
                    data = response.json()
                except ValueError as exc:
                    if attempt == max_retries:
                        raise BitrixIntegrationError("Ошибка Bitrix24 API") from exc
                    await self._backoff(attempt)
                    continue

                error_code = str(data.get("error", ""))
                if error_code in {"QUERY_LIMIT_EXCEEDED", "TOO_MANY_REQUESTS"}:
                    if attempt == max_retries:
                        raise BitrixRateLimitError("Превышен лимит Bitrix24 REST")
                    await self._backoff(attempt)
                    continue

                if data.get("error"):
                    error_code = str(data.get("error", ""))
                    error_description = data.get("error_description") or "Ошибка Bitrix24 API"
                    raise BitrixIntegrationError(f"{error_code}: {error_description}")

                return data
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                logger.warning(
                    "Bitrix REST call failed",
                    extra={"method": method_name, "attempt": attempt, "bot_id": integration.bot_id},
                )
                if attempt == max_retries:
                    raise BitrixIntegrationError("Ошибка соединения с Bitrix24") from exc
                await self._backoff(attempt)

        raise BitrixIntegrationError("Ошибка Bitrix24 API")

    async def _backoff(self, attempt: int) -> None:
        delay = min(2**attempt, 8)
        await asyncio.sleep(delay)

    def parse_state(self, state: str) -> dict[str, Any]:
        return self._verify_state(state)

    async def get_or_create_dialog_link(self, session: AsyncSession, dialog: Dialog) -> BitrixDialogLink:
        result = await session.execute(select(BitrixDialogLink).where(BitrixDialogLink.dialog_id == dialog.id))
        link = result.scalars().first()
        if link:
            return link

        link = BitrixDialogLink(dialog_id=dialog.id, bot_id=dialog.bot_id)
        session.add(link)
        await session.commit()
        await session.refresh(link)
        return link

    async def ensure_connector_registered(self, *, session: AsyncSession | None, integration: BitrixIntegration) -> bool:
        handler_base_url = (settings.public_base_url or "").strip().rstrip("/")
        if not handler_base_url:
            logger.warning(
                "Bitrix24 connector registration skipped: PUBLIC_BASE_URL is not configured",
                extra={"bot_id": integration.bot_id, "portal_url": integration.portal_url},
            )
            return False

        cache_key = (integration.portal_url, str(integration.openline_id or ""))
        if cache_key in self._registered_cache:
            return True

        placement_url = f"{handler_base_url}/integrations/bitrix24/placement"
        event_handler_url = f"{handler_base_url}/integrations/bitrix24/events"
        registration_params = {
            "ID": self.CONNECTOR_ID,
            "NAME": self.CONNECTOR_NAME,
            "PLACEMENT_HANDLER": placement_url,
            "ICON": {
                "DATA_IMAGE": "data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A//www.w3.org/2000/svg%27%20viewBox%3D%270%200%20128%20128%27%3E%3Crect%20width%3D%27128%27%20height%3D%27128%27%20rx%3D%2724%27%20fill%3D%27%231900ff%27/%3E%3Cpath%20fill%3D%27white%27%20d%3D%27M36%2064c0-15.5%2012.5-28%2028-28h28v16H64c-6.6%200-12%205.4-12%2012s5.4%2012%2012%2012h28v16H64c-15.5%200-28-12.5-28-28z%27/%3E%3C/svg%3E",
                "COLOR": "#1900ff",
                "SIZE": "90%",
                "POSITION": "center",
            },
        }

        register_ok = False
        try:
            await self.call_rest(
                session=session,
                integration=integration,
                method_name="imconnector.register",
                params=registration_params,
                max_retries=1,
            )
            register_ok = True
            logger.info(
                "Bitrix24 registered connector serviceai",
                extra={"bot_id": integration.bot_id, "portal_url": integration.portal_url},
            )
        except BitrixIntegrationError as exc:
            error_message = str(exc)
            error_code = error_message.split(":", 1)[0].strip().upper()
            already_exists_codes = {
                "ERROR_CONNECTOR_ALREADY_EXISTS",
                "CONNECTOR_ALREADY_EXISTS",
                "ALREADY_EXISTS",
            }
            if error_code in already_exists_codes:
                register_ok = True
                logger.info(
                    "Bitrix24 connector already exists",
                    extra={"bot_id": integration.bot_id, "portal_url": integration.portal_url},
                )
            else:
                logger.warning(
                    "Bitrix24 connector registration failed",
                    extra={
                        "bot_id": integration.bot_id,
                        "portal_url": integration.portal_url,
                        "error": error_message,
                    },
                )
                return False
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Bitrix24 connector registration failed unexpectedly",
                extra={
                    "bot_id": integration.bot_id,
                    "portal_url": integration.portal_url,
                    "error": str(exc),
                },
                exc_info=True,
            )
            return False

        if not register_ok:
            return False

        data_set_ok = True
        activate_ok = True
        if integration.openline_id:
            try:
                await self.call_rest(
                    session=session,
                    integration=integration,
                    method_name="imconnector.connector.data.set",
                    params={
                        "CONNECTOR": self.CONNECTOR_ID,
                        "LINE": integration.openline_id,
                        "DATA": {
                            "URL": event_handler_url,
                            "URL_IM": event_handler_url,
                            "NAME": self.CONNECTOR_NAME,
                        },
                    },
                    max_retries=1,
                )
            except Exception as exc:  # noqa: BLE001
                data_set_ok = False
                logger.warning(
                    "Bitrix24 connector data.set failed",
                    extra={
                        "bot_id": integration.bot_id,
                        "portal_url": integration.portal_url,
                        "line": integration.openline_id,
                        "error": str(exc),
                    },
                    exc_info=True,
                )

            try:
                await self.call_rest(
                    session=session,
                    integration=integration,
                    method_name="imconnector.activate",
                    params={
                        "CONNECTOR": self.CONNECTOR_ID,
                        "LINE": integration.openline_id,
                        "ACTIVE": "Y",
                    },
                    max_retries=1,
                )
            except Exception as exc:  # noqa: BLE001
                activate_ok = False
                logger.warning(
                    "Bitrix24 connector activate failed",
                    extra={
                        "bot_id": integration.bot_id,
                        "portal_url": integration.portal_url,
                        "line": integration.openline_id,
                        "error": str(exc),
                    },
                    exc_info=True,
                )

        success = register_ok and data_set_ok and activate_ok
        if success:
            self._registered_cache.add(cache_key)
        return success

    async def send_user_message_to_openline(
        self,
        *,
        session: AsyncSession,
        integration: BitrixIntegration,
        dialog: Dialog,
        text: str,
    ) -> BitrixDialogLink:
        link = await self.get_or_create_dialog_link(session=session, dialog=dialog)
        try:
            await self.ensure_connector_registered(session=session, integration=integration)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Bitrix24 connector registration attempt failed before send.messages",
                extra={"bot_id": integration.bot_id, "portal_url": integration.portal_url},
            )

        if not integration.openline_id:
            raise BitrixIntegrationError(
                "Не задана Open Line (LINE) для Bitrix24. "
                "Укажите ID линии в настройках интеграции."
            )

        message_payload = {
            "CONNECTOR": self.connector_name,
            "LINE": integration.openline_id,
            "MESSAGES": [
                {
                    "user": {
                        "id": f"dialog:{dialog.id}",
                        "name": dialog.external_user_id,
                    },
                    "message": {
                        "id": f"msg:{dialog.id}:{int(time.time())}",
                        "date": int(time.time()),
                        "text": text,
                    },
                    "chat": {"id": str(dialog.id)},
                }
            ],
        }

        response = await self.call_rest(
            session=session,
            integration=integration,
            method_name="imconnector.send.messages",
            params=message_payload,
        )

        result = response.get("result") or {}
        chat_id = result.get("chat_id") or result.get("CHAT_ID")
        if chat_id:
            link.bitrix_chat_id = str(chat_id)
            session.add(link)
            await session.commit()
            await session.refresh(link)

        await self.call_rest(
            session=session,
            integration=integration,
            method_name="imconnector.send.status.delivery",
            params={
                "CONNECTOR": self.connector_name,
                "LINE": integration.openline_id,
                "MESSAGES": [{"im": {"chat_id": link.bitrix_chat_id or str(dialog.id)}}],
            },
        )

        return link

    async def create_lead_for_dialog(
        self,
        *,
        session: AsyncSession,
        integration: BitrixIntegration,
        dialog: Dialog,
    ) -> BitrixDialogLink:
        link = await self.get_or_create_dialog_link(session=session, dialog=dialog)
        if not link.bitrix_chat_id:
            raise BitrixIntegrationError("Диалог ещё не создан в Bitrix24")

        response = await self.call_rest(
            session=session,
            integration=integration,
            method_name="imopenlines.crm.lead.create",
            params={"CHAT_ID": link.bitrix_chat_id},
        )
        result = response.get("result")
        lead_id = result.get("ID") if isinstance(result, dict) else result
        if not lead_id:
            raise BitrixIntegrationError("Не удалось создать лид")

        link.bitrix_lead_id = int(lead_id)
        session.add(link)
        await session.commit()
        await session.refresh(link)
        return link

    async def sync_incoming_user_message(
        self,
        *,
        bot_id: int,
        dialog_id: int,
        text: str | None,
        dialog_created: bool,
    ) -> None:
        if not (text and text.strip()):
            return

        async def _sync() -> None:
            async with async_session_factory() as session:
                integration = await self.ensure_active_integration(session=session, bot_id=bot_id)
                if integration is None:
                    return

                result = await session.execute(select(Dialog).where(Dialog.id == dialog_id))
                dialog = result.scalars().first()
                if dialog is None:
                    return

                link = await self.send_user_message_to_openline(
                    session=session,
                    integration=integration,
                    dialog=dialog,
                    text=text,
                )
                if dialog_created and integration.auto_create_lead_on_first_message and not link.bitrix_lead_id:
                    await self.create_lead_for_dialog(
                        session=session,
                        integration=integration,
                        dialog=dialog,
                    )

        try:
            await asyncio.wait_for(_sync(), timeout=3.0)
        except asyncio.TimeoutError:
            logger.warning("Bitrix24 integration timeout", extra={"bot_id": bot_id, "dialog_id": dialog_id})
        except BitrixIntegrationError as exc:
            if "подходящий провайдер" in str(exc).lower():
                logger.error(
                    "Bitrix24 connector is not registered: failed to send message to OpenLines",
                    extra={"bot_id": bot_id, "dialog_id": dialog_id, "error": str(exc)},
                )
            logger.exception(
                "Bitrix24 integration error for bot_id=%s dialog_id=%s: %s",
                bot_id,
                dialog_id,
                str(exc),
                extra={"bot_id": bot_id, "dialog_id": dialog_id, "error": str(exc)},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Bitrix24 background sync failed",
                extra={"bot_id": bot_id, "dialog_id": dialog_id, "error": str(exc)},
                exc_info=True,
            )
