from __future__ import annotations

import hmac
import json
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db_session, require_bot_access
from app.modules.accounts.models import User
from app.modules.channels.sender_registry import get_sender
from app.modules.dialogs.models import Dialog, MessageSender
from app.modules.dialogs.schemas import DialogMessageOut, DialogOut
from app.modules.dialogs.service import DialogsService
from app.modules.dialogs.websocket_manager import manager
from app.modules.integrations.bitrix24.models import BitrixDialogLink, BitrixIntegration
from app.modules.integrations.bitrix24.schemas import (
    BitrixConnectRequest,
    BitrixConnectResponse,
    BitrixDisconnectRequest,
    BitrixEventPayload,
    BitrixSettingsUpdateRequest,
    BitrixStatusResponse,
)
from app.modules.integrations.bitrix24.service import (
    Bitrix24Service,
    BitrixIntegrationError,
)
from app.security.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations/bitrix24", tags=["integrations"])


def _extract_dialog_id(raw: str | int | None) -> int | None:
    if raw is None:
        return None
    normalized = str(raw).strip()
    for prefix in ("dialog:", "chat:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
    return int(normalized) if normalized.isdigit() else None


def _extract_hosts_from_auth(auth: dict) -> list[str]:
    hosts: list[str] = []
    for key in ("domain", "server_domain"):
        value = auth.get(key)
        if value:
            hosts.append(str(value).strip().lower())
    for key in ("client_endpoint", "server_endpoint"):
        endpoint = auth.get(key)
        if endpoint:
            parsed = urlparse(str(endpoint))
            if parsed.netloc:
                hosts.append(parsed.netloc.lower())
    return [host for host in hosts if host]


async def _resolve_dialog_for_event(
    session: AsyncSession, payload: BitrixEventPayload
) -> Dialog | None:
    data = payload.data or {}

    user_info = data.get("user") if isinstance(data.get("user"), dict) else {}
    chat_info = data.get("chat") if isinstance(data.get("chat"), dict) else {}

    dialog_id_candidates = [
        data.get("dialog_id"),
        user_info.get("id"),
        chat_info.get("id"),
        data.get("chat", {}).get("id") if isinstance(data.get("chat"), dict) else None,
    ]

    for candidate in dialog_id_candidates:
        dialog_id = _extract_dialog_id(candidate)
        if dialog_id is None:
            continue
        result = await session.execute(select(Dialog).where(Dialog.id == dialog_id))
        dialog = result.scalars().first()
        if dialog:
            return dialog

    bitrix_chat_id = data.get("chat_id") or chat_info.get("id")
    if bitrix_chat_id is None:
        return None

    link_result = await session.execute(
        select(BitrixDialogLink).where(
            BitrixDialogLink.bitrix_chat_id == str(bitrix_chat_id)
        )
    )
    link = link_result.scalars().first()
    if not link:
        return None

    result = await session.execute(select(Dialog).where(Dialog.id == link.dialog_id))
    return result.scalars().first()


@router.post("/connect", response_model=BitrixConnectResponse)
async def connect_bitrix24(
    payload: BitrixConnectRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    bitrix_service: Bitrix24Service = Depends(Bitrix24Service),
) -> BitrixConnectResponse:
    await require_bot_access(payload.bot_id, session, current_user)

    if (
        not settings.bitrix24_app_client_id
        or not settings.bitrix24_app_client_secret
        or not settings.bitrix24_app_redirect_url
        or not settings.bitrix24_connect_state_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bitrix24 OAuth не настроен",
        )

    try:
        portal_url = bitrix_service.normalize_portal_url(payload.portal_domain)
        auth_url = bitrix_service.build_auth_url(
            bot_id=payload.bot_id, portal_url=portal_url
        )
    except BitrixIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return BitrixConnectResponse(auth_url=auth_url)


@router.get("/oauth/callback")
async def bitrix_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    bitrix_service: Bitrix24Service = Depends(Bitrix24Service),
) -> RedirectResponse:
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth callback params",
        )

    if (
        not settings.bitrix24_app_client_id
        or not settings.bitrix24_app_client_secret
        or not settings.bitrix24_app_redirect_url
        or not settings.bitrix24_connect_state_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bitrix24 OAuth не настроен",
        )

    try:
        state_data = bitrix_service.parse_state(state)
        bot_id = int(state_data["bot_id"])
        portal_url = str(state_data["portal_url"])
        token_data = await bitrix_service.exchange_code(
            code=code, portal_url=portal_url
        )
    except BitrixIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    result = await session.execute(
        select(BitrixIntegration).where(BitrixIntegration.bot_id == bot_id)
    )
    integration = result.scalars().first()
    if not integration:
        integration = BitrixIntegration(bot_id=bot_id, portal_url=portal_url)

    expires_in = int(token_data.get("expires_in", 3600))
    integration.portal_url = portal_url
    integration.member_id = token_data.get("member_id")
    integration.access_token = token_data.get("access_token")
    integration.refresh_token = token_data.get("refresh_token")
    integration.expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        seconds=expires_in - 30
    )
    integration.scope = token_data.get("scope")
    integration.enabled = True
    integration.updated_at = datetime.now(UTC).replace(tzinfo=None)

    session.add(integration)
    await session.commit()

    frontend_base = settings.frontend_base_url or "http://localhost:3000"
    return RedirectResponse(
        url=f"{frontend_base}/integrations?bot={bot_id}&success=1", status_code=302
    )


@router.get("/status", response_model=BitrixStatusResponse)
async def bitrix_status(
    bot_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    bitrix_service: Bitrix24Service = Depends(Bitrix24Service),
) -> BitrixStatusResponse:
    await require_bot_access(bot_id, session, current_user)
    integration = await bitrix_service.get_integration(session=session, bot_id=bot_id)
    if not integration or not integration.enabled or not integration.access_token:
        return BitrixStatusResponse(
            connected=False,
            enabled=False,
            openline_id=integration.openline_id if integration else None,
        )

    return BitrixStatusResponse(
        connected=True,
        enabled=integration.enabled,
        portal_url=integration.portal_url,
        connected_at=integration.created_at,
        openline_id=integration.openline_id,
        auto_create_lead_on_first_message=integration.auto_create_lead_on_first_message,
    )


@router.post("/disconnect", response_model=BitrixStatusResponse)
async def disconnect_bitrix24(
    payload: BitrixDisconnectRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    bitrix_service: Bitrix24Service = Depends(Bitrix24Service),
) -> BitrixStatusResponse:
    await require_bot_access(payload.bot_id, session, current_user)
    integration = await bitrix_service.get_integration(
        session=session, bot_id=payload.bot_id
    )
    if integration:
        integration.enabled = False
        integration.access_token = None
        integration.refresh_token = None
        integration.expires_at = None
        session.add(integration)
        await session.commit()

    return BitrixStatusResponse(
        connected=False,
        enabled=False,
        openline_id=integration.openline_id if integration else None,
    )


@router.patch("/settings", response_model=BitrixStatusResponse)
async def update_bitrix24_settings(
    payload: BitrixSettingsUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    bitrix_service: Bitrix24Service = Depends(Bitrix24Service),
) -> BitrixStatusResponse:
    await require_bot_access(payload.bot_id, session, current_user)
    integration = await bitrix_service.get_integration(
        session=session, bot_id=payload.bot_id
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Интеграция не подключена"
        )

    integration.auto_create_lead_on_first_message = (
        payload.auto_create_lead_on_first_message
    )
    integration.openline_id = (payload.openline_id or "").strip() or None
    session.add(integration)
    await session.commit()
    await session.refresh(integration)

    return BitrixStatusResponse(
        connected=bool(integration.enabled and integration.access_token),
        enabled=integration.enabled,
        portal_url=integration.portal_url,
        connected_at=integration.created_at,
        openline_id=integration.openline_id,
        auto_create_lead_on_first_message=integration.auto_create_lead_on_first_message,
    )


@router.post("/dialogs/{dialog_id}/create_lead")
async def create_lead_for_dialog(
    dialog_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    bitrix_service: Bitrix24Service = Depends(Bitrix24Service),
) -> dict:
    dialog_result = await session.execute(select(Dialog).where(Dialog.id == dialog_id))
    dialog = dialog_result.scalars().first()
    if not dialog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found"
        )

    await require_bot_access(dialog.bot_id, session, current_user)

    integration = await bitrix_service.ensure_active_integration(
        session=session, bot_id=dialog.bot_id
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Интеграция отключена администратором",
        )

    try:
        link = await bitrix_service.create_lead_for_dialog(
            session=session, integration=integration, dialog=dialog
        )
    except BitrixIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return {"dialog_id": dialog.id, "bitrix_lead_id": link.bitrix_lead_id}


@router.post("/events")
async def bitrix_events(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    dialogs_service: DialogsService = Depends(DialogsService),
    bitrix_service: Bitrix24Service = Depends(Bitrix24Service),
) -> dict[str, str]:
    payload_dict: dict | None = None
    try:
        parsed_json = await request.json()
        if isinstance(parsed_json, dict):
            payload_dict = parsed_json
    except Exception:
        payload_dict = None

    if payload_dict is None:
        try:
            form_data = await request.form()
        except Exception:
            form_data = None

        payload_dict = {}
        auth_dict: dict[str, str] = {}
        data_dict: dict = {}

        def set_nested(target: dict, path: list[str], value: str) -> None:
            cursor = target
            for key in path[:-1]:
                nested = cursor.get(key)
                if not isinstance(nested, dict):
                    nested = {}
                    cursor[key] = nested
                cursor = nested
            cursor[path[-1]] = value

        if form_data is not None:
            for key, value in form_data.multi_items():
                value_str = str(value)

                if key == "event":
                    payload_dict["event"] = value_str
                    continue

                if key == "auth":
                    try:
                        parsed_auth = json.loads(value_str)
                        if isinstance(parsed_auth, dict):
                            auth_dict.update({str(k): str(v) for k, v in parsed_auth.items()})
                    except Exception:
                        pass
                    continue

                if key.startswith("auth[") and key.endswith("]"):
                    auth_key = key[5:-1]
                    if auth_key:
                        auth_dict[auth_key] = value_str
                    continue

                if key == "data":
                    try:
                        parsed_data = json.loads(value_str)
                        if isinstance(parsed_data, dict):
                            data_dict.update(parsed_data)
                    except Exception:
                        pass
                    continue

                if key.startswith("data["):
                    path = [segment for segment in key[5:].replace("]", "").split("[") if segment]
                    supported_paths = {
                        ("message", "text"),
                        ("text",),
                        ("chat", "id"),
                        ("chat_id",),
                        ("user", "id"),
                        ("dialog_id",),
                    }
                    if tuple(path) in supported_paths:
                        set_nested(data_dict, path, value_str)

        if auth_dict:
            payload_dict["auth"] = auth_dict
        if data_dict:
            payload_dict["data"] = data_dict

    event = payload_dict.get("event") if isinstance(payload_dict, dict) else None
    data = payload_dict.get("data") if isinstance(payload_dict, dict) else None
    auth = payload_dict.get("auth") if isinstance(payload_dict, dict) else None

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            data = None

    if isinstance(auth, str):
        try:
            auth = json.loads(auth)
        except Exception:
            auth = None

    if data is not None and not isinstance(data, dict):
        data = None
    if auth is not None and not isinstance(auth, dict):
        auth = None

    payload = BitrixEventPayload(event=event, data=data, auth=auth)

    if not settings.bitrix24_app_application_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bitrix24 webhook не настроен",
        )

    auth = payload.auth or {}
    application_token = str(auth.get("application_token") or "")
    if not application_token or not hmac.compare_digest(
        application_token, settings.bitrix24_app_application_token
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    event_name = (payload.event or "").lower()
    if "message" not in event_name:
        return {"status": "ignored"}

    dialog = await _resolve_dialog_for_event(session=session, payload=payload)
    if not dialog:
        return {"status": "ignored"}

    integration = await bitrix_service.get_integration(
        session=session, bot_id=dialog.bot_id
    )
    if not integration or not integration.enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    auth_member_id = auth.get("member_id")
    if auth_member_id and integration.member_id:
        if not hmac.compare_digest(str(auth_member_id), str(integration.member_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )
    else:
        integration_host = (urlparse(integration.portal_url).netloc or "").lower()
        auth_hosts = _extract_hosts_from_auth(auth)
        if not integration_host or not auth_hosts:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )
        host_match = any(
            hmac.compare_digest(host, integration_host) for host in auth_hosts
        )
        if not host_match:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )

    data = payload.data or {}
    text = (
        data.get("message", {}).get("text")
        if isinstance(data.get("message"), dict)
        else None
    )
    text = text or data.get("text")
    if not text:
        return {"status": "ignored"}

    message, updated_dialog, _ = await dialogs_service.add_message(
        session=session,
        bot_id=dialog.bot_id,
        channel_type=dialog.channel_type,
        external_chat_id=dialog.external_chat_id,
        external_user_id=dialog.external_user_id,
        sender=MessageSender.OPERATOR,
        text=text,
        payload={"source": "bitrix24"},
    )

    sender_cls = get_sender(dialog.channel_type)
    await sender_cls().send_text(
        bot_id=dialog.bot_id, external_chat_id=dialog.external_chat_id, text=text
    )

    dialog_payload = DialogOut.model_validate(updated_dialog).model_dump()
    message_payload = DialogMessageOut.model_validate(message).model_dump()
    admin_targets = (
        [updated_dialog.assigned_admin_id]
        if updated_dialog.assigned_admin_id is not None
        else None
    )

    await manager.broadcast_to_admins(
        {"event": "message_created", "data": message_payload}, admin_ids=admin_targets
    )
    await manager.broadcast_to_admins(
        {"event": "dialog_updated", "data": dialog_payload}, admin_ids=admin_targets
    )
    await manager.broadcast_to_webchat(
        bot_id=updated_dialog.bot_id,
        session_id=updated_dialog.external_chat_id,
        message={"event": "message_created", "data": message_payload},
    )
    await manager.broadcast_to_webchat(
        bot_id=updated_dialog.bot_id,
        session_id=updated_dialog.external_chat_id,
        message={"event": "dialog_updated", "data": dialog_payload},
    )

    logger.info(
        "Bitrix operator message delivered",
        extra={
            "dialog_id": dialog.id,
            "bot_id": dialog.bot_id,
            "event_name": event_name,
        },
    )
    return {"status": "ok"}
