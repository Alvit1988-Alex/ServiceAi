"""Channels router."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.modules.accounts.models import User
from app.modules.ai.service import AIService, get_ai_service
from app.modules.channels.schemas import (
    BotChannelCreate,
    BotChannelOut,
    BotChannelUpdate,
    ListResponse,
    NormalizedIncomingMessage,
)
from app.modules.channels.service import ChannelsService, sync_telegram_webhook
from app.modules.channels.telegram_handler import normalize_telegram_update
from app.modules.channels.avito_handler import normalize_avito_update
from app.modules.channels.max_handler import normalize_max_webhook
from app.modules.channels.webchat_handler import normalize_webchat_message
from app.modules.channels.whatsapp_360_handler import normalize_whatsapp_360_webhook
from app.modules.channels.whatsapp_custom_handler import normalize_whatsapp_custom_webhook
from app.modules.channels.whatsapp_green_handler import normalize_whatsapp_green_notification
from app.modules.channels.models import ChannelType
from app.modules.dialogs.schemas import DialogMessageOut, DialogOut
from app.modules.dialogs.service import DialogsService
from app.modules.dialogs.websocket_manager import manager
from app.security.auth import get_current_user

router = APIRouter(prefix="/bots/{bot_id}/channels", tags=["channels"])
logger = logging.getLogger(__name__)
AVITO_SIGNATURE_HEADER = "X-Avito-Signature"


def _ensure_channel_available(channel) -> None:
    if not channel or not channel.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")


def _validate_secret(expected: str | None, provided: str | None, detail: str) -> None:
    if expected and expected != provided:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def _process_and_broadcast(
    *,
    normalized: NormalizedIncomingMessage,
    dialogs_service: DialogsService,
    ai_service: AIService,
    session: AsyncSession,
) -> None:
    user_message, bot_message, dialog, dialog_created = await dialogs_service.process_incoming_message(
        session=session, incoming_message=normalized, ai_service=ai_service
    )

    messages = [user_message]
    if bot_message:
        messages.append(bot_message)

    await _broadcast_message_events(messages=messages, dialog=dialog, dialog_created=dialog_created)


async def _broadcast_message_events(messages, dialog, dialog_created: bool) -> None:
    dialog_payload = DialogOut.model_validate(dialog).model_dump()
    admin_targets = [dialog.assigned_admin_id] if dialog.assigned_admin_id is not None else None

    if dialog_created:
        await manager.broadcast_to_admins({"event": "dialog_created", "data": dialog_payload}, admin_ids=admin_targets)
        await manager.broadcast_to_webchat(
            bot_id=dialog_payload["bot_id"],
            session_id=dialog_payload["external_chat_id"],
            message={"event": "dialog_created", "data": dialog_payload},
        )

    for message in messages:
        message_payload = DialogMessageOut.model_validate(message).model_dump()
        await manager.broadcast_to_admins({"event": "message_created", "data": message_payload}, admin_ids=admin_targets)
        await manager.broadcast_to_admins({"event": "dialog_updated", "data": dialog_payload}, admin_ids=admin_targets)

        await manager.broadcast_to_webchat(
            bot_id=dialog_payload["bot_id"],
            session_id=dialog_payload["external_chat_id"],
            message={"event": "message_created", "data": message_payload},
        )
        await manager.broadcast_to_webchat(
            bot_id=dialog_payload["bot_id"],
            session_id=dialog_payload["external_chat_id"],
            message={"event": "dialog_updated", "data": dialog_payload},
        )


@router.post("", response_model=BotChannelOut, status_code=status.HTTP_201_CREATED)
async def create_channel(
    bot_id: int,
    data: BotChannelCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ChannelsService = Depends(ChannelsService),
) -> BotChannelOut:
    channel = await service.create(session=session, bot_id=bot_id, obj_in=data)
    return service.decrypt(channel)


@router.get("", response_model=ListResponse[BotChannelOut])
async def list_channels(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ChannelsService = Depends(ChannelsService),
) -> ListResponse[BotChannelOut]:
    items = service.decrypt_many(await service.list(session=session, bot_id=bot_id))
    return ListResponse[BotChannelOut](items=items)


@router.get("/{channel_id}", response_model=BotChannelOut)
async def get_channel(
    bot_id: int,
    channel_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ChannelsService = Depends(ChannelsService),
) -> BotChannelOut:
    channel = await service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return service.decrypt(channel)


@router.patch("/{channel_id}", response_model=BotChannelOut)
async def update_channel(
    bot_id: int,
    channel_id: int,
    data: BotChannelUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ChannelsService = Depends(ChannelsService),
) -> BotChannelOut:
    channel = await service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    updated = await service.update(session=session, db_obj=channel, obj_in=data)
    decrypted = service.decrypt(updated)

    if decrypted.channel_type == ChannelType.TELEGRAM:
        status, error = await sync_telegram_webhook(decrypted)
        decrypted.config = dict(decrypted.config or {})
        if status:
            decrypted.config["webhook_status"] = status
        if error:
            decrypted.config["webhook_error"] = error
        elif "webhook_error" in decrypted.config:
            decrypted.config.pop("webhook_error")

    return decrypted


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    bot_id: int,
    channel_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ChannelsService = Depends(ChannelsService),
) -> None:
    channel = await service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    await service.delete(session=session, bot_id=bot_id, channel_id=channel_id)


@router.post("/webhooks/telegram/{channel_id}")
async def telegram_webhook(
    bot_id: int,
    channel_id: int,
    payload: dict,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    channels_service: ChannelsService = Depends(ChannelsService),
    dialogs_service: DialogsService = Depends(DialogsService),
    ai_service: AIService = Depends(get_ai_service),
) -> dict:
    channel = await channels_service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    _ensure_channel_available(channel)
    channel = channels_service.decrypt(channel)

    expected_secret = channel.config.get("secret_token") or channel.config.get("token")
    provided_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    _validate_secret(expected_secret, provided_secret, "Invalid Telegram secret token")

    normalized = normalize_telegram_update(bot_id=bot_id, channel_id=channel_id, update=payload)

    await _process_and_broadcast(
        normalized=normalized,
        dialogs_service=dialogs_service,
        ai_service=ai_service,
        session=session,
    )
    return {"ok": True}


def _extract_provided_secret(request: Request, payload: dict, header_name: str = "X-Webhook-Secret") -> str | None:
    return request.headers.get(header_name) or payload.get("secret") or payload.get("token")


@router.post("/webhooks/whatsapp/green/{channel_id}")
async def whatsapp_green_webhook(
    bot_id: int,
    channel_id: int,
    payload: dict,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    channels_service: ChannelsService = Depends(ChannelsService),
    dialogs_service: DialogsService = Depends(DialogsService),
    ai_service: AIService = Depends(get_ai_service),
) -> dict:
    channel = await channels_service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    _ensure_channel_available(channel)
    channel = channels_service.decrypt(channel)

    expected_secret = channel.config.get("secret") or channel.config.get("webhook_secret")
    provided_secret = _extract_provided_secret(request=request, payload=payload)
    _validate_secret(expected_secret, provided_secret, "Invalid WhatsApp Green secret")

    normalized = normalize_whatsapp_green_notification(
        bot_id=bot_id, channel_id=channel_id, notification=payload
    )

    await _process_and_broadcast(
        normalized=normalized,
        dialogs_service=dialogs_service,
        ai_service=ai_service,
        session=session,
    )
    return {"status": "ok"}


@router.post("/webhooks/whatsapp/360/{channel_id}")
async def whatsapp_360_webhook(
    bot_id: int,
    channel_id: int,
    payload: dict,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    channels_service: ChannelsService = Depends(ChannelsService),
    dialogs_service: DialogsService = Depends(DialogsService),
    ai_service: AIService = Depends(get_ai_service),
) -> dict:
    channel = await channels_service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    _ensure_channel_available(channel)
    channel = channels_service.decrypt(channel)

    expected_secret = channel.config.get("secret") or channel.config.get("webhook_secret")
    provided_secret = _extract_provided_secret(request=request, payload=payload)
    _validate_secret(expected_secret, provided_secret, "Invalid WhatsApp 360 secret")

    normalized = normalize_whatsapp_360_webhook(bot_id=bot_id, channel_id=channel_id, payload=payload)

    await _process_and_broadcast(
        normalized=normalized,
        dialogs_service=dialogs_service,
        ai_service=ai_service,
        session=session,
    )
    return {"status": "ok"}


@router.post("/webhooks/whatsapp/custom/{channel_id}")
async def whatsapp_custom_webhook(
    bot_id: int,
    channel_id: int,
    payload: dict,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    channels_service: ChannelsService = Depends(ChannelsService),
    dialogs_service: DialogsService = Depends(DialogsService),
    ai_service: AIService = Depends(get_ai_service),
) -> dict:
    channel = await channels_service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    _ensure_channel_available(channel)
    channel = channels_service.decrypt(channel)

    expected_secret = channel.config.get("secret") or channel.config.get("webhook_secret")
    provided_secret = _extract_provided_secret(request=request, payload=payload)
    _validate_secret(expected_secret, provided_secret, "Invalid WhatsApp custom secret")

    normalized = normalize_whatsapp_custom_webhook(
        bot_id=bot_id, channel_id=channel_id, payload=payload, headers=dict(request.headers)
    )

    await _process_and_broadcast(
        normalized=normalized,
        dialogs_service=dialogs_service,
        ai_service=ai_service,
        session=session,
    )
    return {"status": "ok"}


@router.post("/webhooks/avito/{channel_id}")
async def avito_webhook(
    bot_id: int,
    channel_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    channels_service: ChannelsService = Depends(ChannelsService),
    dialogs_service: DialogsService = Depends(DialogsService),
    ai_service: AIService = Depends(get_ai_service),
) -> dict:
    raw_body = await request.body()

    channel = await channels_service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    _ensure_channel_available(channel)
    channel = channels_service.decrypt(channel)

    expected_secret = channel.config.get("webhook_secret") or channel.config.get("secret")
    provided_secret = request.query_params.get("secret")

    if not expected_secret:
        logger.warning(
            "Avito webhook secret is not configured; rejecting webhook",
            extra={"bot_id": bot_id, "channel_id": channel_id},
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Avito webhook secret not configured")

    if expected_secret != provided_secret:
        logger.warning(
            "Invalid Avito webhook secret",
            extra={"bot_id": bot_id, "channel_id": channel_id},
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Avito webhook secret")

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    normalized = normalize_avito_update(bot_id=bot_id, channel_id=channel_id, update=payload)

    payload_meta = normalized.payload or {}
    if payload_meta.get("skip_processing"):
        logger.info(
            "Avito webhook skipped",
            extra={
                "bot_id": bot_id,
                "channel_id": channel_id,
                "conversation_id": normalized.external_chat_id,
                "item_id": normalized.item_id,
                "reason": payload_meta.get("skip_reason"),
            },
        )
        return {"status": "skipped", "reason": payload_meta.get("skip_reason")}

    logger.info(
        "Avito webhook received",
        extra={
            "bot_id": bot_id,
            "channel_id": channel_id,
            "conversation_id": normalized.external_chat_id,
            "item_id": normalized.item_id,
        },
    )

    should_reply, reason = channels_service.should_reply_to_avito_message(
        channel.config, normalized.item_id
    )
    if not should_reply:
        logger.info(
            "Avito message filtered",
            extra={
                "bot_id": bot_id,
                "channel_id": channel_id,
                "conversation_id": normalized.external_chat_id,
                "item_id": normalized.item_id,
                "reason": reason,
            },
        )
        return {"status": "filtered", "reason": reason}

    await _process_and_broadcast(
        normalized=normalized,
        dialogs_service=dialogs_service,
        ai_service=ai_service,
        session=session,
    )
    return {"result": "ok"}


@router.post("/webhooks/max/{channel_id}")
async def max_webhook(
    bot_id: int,
    channel_id: int,
    payload: dict,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    channels_service: ChannelsService = Depends(ChannelsService),
    dialogs_service: DialogsService = Depends(DialogsService),
    ai_service: AIService = Depends(get_ai_service),
) -> dict:
    channel = await channels_service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    _ensure_channel_available(channel)
    channel = channels_service.decrypt(channel)

    expected_secret = channel.config.get("secret") or channel.config.get("token")
    provided_secret = _extract_provided_secret(request=request, payload=payload)
    _validate_secret(expected_secret, provided_secret, "Invalid Max webhook secret")

    normalized = normalize_max_webhook(
        bot_id=bot_id, channel_id=channel_id, payload=payload, headers=dict(request.headers)
    )

    await _process_and_broadcast(
        normalized=normalized,
        dialogs_service=dialogs_service,
        ai_service=ai_service,
        session=session,
    )
    return {"status": "ok"}


@router.post("/webhooks/webchat/{channel_id}")
async def webchat_webhook(
    bot_id: int,
    channel_id: int,
    payload: dict,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    channels_service: ChannelsService = Depends(ChannelsService),
    dialogs_service: DialogsService = Depends(DialogsService),
    ai_service: AIService = Depends(get_ai_service),
) -> dict:
    channel = await channels_service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    _ensure_channel_available(channel)
    channel = channels_service.decrypt(channel)

    expected_secret = channel.config.get("secret") or channel.config.get("token")
    provided_secret = _extract_provided_secret(request=request, payload=payload, header_name="X-Webchat-Secret")
    _validate_secret(expected_secret, provided_secret, "Invalid webchat secret")

    normalized = normalize_webchat_message(bot_id=bot_id, channel_id=channel_id, payload=payload)

    await _process_and_broadcast(
        normalized=normalized,
        dialogs_service=dialogs_service,
        ai_service=ai_service,
        session=session,
    )
    return {"status": "ok"}
