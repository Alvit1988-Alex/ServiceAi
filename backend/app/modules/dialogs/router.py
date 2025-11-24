"""Dialogs API router."""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.modules.accounts.models import User
from app.modules.channels.models import ChannelType
from app.modules.dialogs.models import DialogStatus, MessageSender
from app.modules.dialogs.schemas import DialogDetail, DialogMessageOut, DialogShort, ListResponse
from app.modules.dialogs.service import DialogLockError, DialogMessagesService, DialogsService
from app.modules.dialogs.websocket_manager import manager
from app.security.auth import get_current_user
from app.security.jwt import decode_access_token
from app.utils.validators import validate_pagination

router = APIRouter(tags=["dialogs"])


class OperatorMessageIn(BaseModel):
    text: str | None = None
    payload: dict | None = None


def _resolve_admin_targets(dialog_payload: dict) -> list[int] | None:
    admin_id = dialog_payload.get("assigned_admin_id")
    return [admin_id] if admin_id is not None else None


@router.get("/bots/{bot_id}/dialogs", response_model=ListResponse[DialogShort])
async def list_dialogs(
    bot_id: int,
    status: DialogStatus | None = None,
    channel_type: ChannelType | None = None,
    assigned_admin_id: int | None = None,
    external_chat_id: str | None = None,
    closed: bool | None = None,
    is_locked: bool | None = None,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogsService = Depends(DialogsService),
) -> ListResponse[DialogShort]:
    validate_pagination(page, per_page)

    dialogs, total, has_next = await service.list(
        session=session,
        filters={
            "bot_id": bot_id,
            "status": status,
            "channel_type": channel_type,
            "assigned_admin_id": assigned_admin_id,
            "external_chat_id": external_chat_id,
            "closed": closed,
            "is_locked": is_locked,
        },
        page=page,
        per_page=per_page,
        include_messages=True,
    )

    items = [
        DialogShort.model_validate(dialog, update={"last_message": dialog.messages[-1] if dialog.messages else None})
        for dialog in dialogs
    ]

    return ListResponse[DialogShort](
        items=items,
        page=page,
        per_page=per_page,
        total=total,
        has_next=has_next,
    )


@router.get("/bots/{bot_id}/search", response_model=ListResponse[DialogShort])
async def search_dialogs(
    bot_id: int,
    query: str | None = None,
    status: DialogStatus | None = None,
    assigned_admin_id: int | None = None,
    channel_type: ChannelType | None = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogsService = Depends(DialogsService),
) -> ListResponse[DialogShort]:
    validate_pagination(1, limit)
    if offset < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="offset must be >= 0")

    dialogs, total, has_next = await service.search_dialogs(
        session=session,
        bot_id=bot_id,
        query=query,
        status=status,
        assigned_admin_id=assigned_admin_id,
        channel_type=channel_type,
        limit=limit,
        offset=offset,
    )

    items = [
        DialogShort.model_validate(dialog, update={"last_message": dialog.messages[-1] if dialog.messages else None})
        for dialog in dialogs
    ]

    page = offset // limit + 1 if limit else 1

    return ListResponse[DialogShort](
        items=items,
        page=page,
        per_page=limit,
        total=total,
        has_next=has_next,
    )


@router.get("/bots/{bot_id}/dialogs/{dialog_id}", response_model=DialogDetail)
async def get_dialog(
    bot_id: int,
    dialog_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogsService = Depends(DialogsService),
) -> DialogDetail:
    dialog = await service.get(session=session, bot_id=bot_id, dialog_id=dialog_id, include_messages=True)
    if not dialog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found")
    messages = sorted(dialog.messages, key=lambda m: m.created_at) if dialog.messages else []
    return DialogDetail.model_validate(dialog, update={"messages": messages})


@router.post("/bots/{bot_id}/dialogs/{dialog_id}/close", response_model=DialogDetail)
async def close_dialog(
    bot_id: int,
    dialog_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogsService = Depends(DialogsService),
) -> DialogDetail:
    dialog = await service.get(session=session, bot_id=bot_id, dialog_id=dialog_id, include_messages=True)
    if not dialog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found")
    if dialog.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dialog is already closed")

    dialog = await service.close_dialog(session=session, dialog=dialog)

    dialog = await service.get(session=session, bot_id=bot_id, dialog_id=dialog_id, include_messages=True)
    dialog_payload = DialogDetail.model_validate(
        dialog, update={"messages": sorted(dialog.messages, key=lambda m: m.created_at)} if dialog else {}
    ).model_dump()

    admin_targets = _resolve_admin_targets(dialog_payload)

    await manager.broadcast_to_admins({"event": "dialog_updated", "data": dialog_payload}, admin_ids=admin_targets)
    await manager.broadcast_to_webchat(
        bot_id=dialog_payload["bot_id"],
        session_id=dialog_payload["external_chat_id"],
        message={"event": "dialog_updated", "data": dialog_payload},
    )

    return DialogDetail.model_validate(dialog, update={"messages": sorted(dialog.messages, key=lambda m: m.created_at)})


@router.post("/bots/{bot_id}/dialogs/{dialog_id}/lock", response_model=DialogDetail)
async def lock_dialog(
    bot_id: int,
    dialog_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogsService = Depends(DialogsService),
) -> DialogDetail:
    dialog = await service.get(session=session, bot_id=bot_id, dialog_id=dialog_id, include_messages=True)
    if not dialog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found")

    try:
        await service.lock_dialog(session=session, dialog=dialog, admin_id=current_user.id)
    except DialogLockError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    dialog = await service.get(session=session, bot_id=bot_id, dialog_id=dialog_id, include_messages=True)
    dialog_payload = DialogDetail.model_validate(
        dialog, update={"messages": sorted(dialog.messages, key=lambda m: m.created_at)} if dialog else {}
    ).model_dump()

    admin_targets = _resolve_admin_targets(dialog_payload)

    await manager.broadcast_to_admins({"event": "dialog_locked", "data": dialog_payload}, admin_ids=admin_targets)
    await manager.broadcast_to_webchat(
        bot_id=dialog_payload["bot_id"],
        session_id=dialog_payload["external_chat_id"],
        message={"event": "dialog_locked", "data": dialog_payload},
    )

    return DialogDetail.model_validate(dialog, update={"messages": sorted(dialog.messages, key=lambda m: m.created_at)})


@router.post("/bots/{bot_id}/dialogs/{dialog_id}/unlock", response_model=DialogDetail)
async def unlock_dialog(
    bot_id: int,
    dialog_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogsService = Depends(DialogsService),
) -> DialogDetail:
    dialog = await service.get(session=session, bot_id=bot_id, dialog_id=dialog_id, include_messages=True)
    if not dialog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found")

    try:
        await service.unlock_dialog(session=session, dialog=dialog, admin_id=current_user.id)
    except DialogLockError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    dialog = await service.get(session=session, bot_id=bot_id, dialog_id=dialog_id, include_messages=True)
    dialog_payload = DialogDetail.model_validate(
        dialog, update={"messages": sorted(dialog.messages, key=lambda m: m.created_at)} if dialog else {}
    ).model_dump()

    admin_targets = _resolve_admin_targets(dialog_payload)

    await manager.broadcast_to_admins({"event": "dialog_unlocked", "data": dialog_payload}, admin_ids=admin_targets)
    await manager.broadcast_to_webchat(
        bot_id=dialog_payload["bot_id"],
        session_id=dialog_payload["external_chat_id"],
        message={"event": "dialog_unlocked", "data": dialog_payload},
    )

    return DialogDetail.model_validate(dialog, update={"messages": sorted(dialog.messages, key=lambda m: m.created_at)})


@router.delete("/bots/{bot_id}/dialogs/{dialog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dialog(
    bot_id: int,
    dialog_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogsService = Depends(DialogsService),
) -> None:
    dialog = await service.get(session=session, bot_id=bot_id, dialog_id=dialog_id)
    if not dialog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found")
    await service.delete(session=session, bot_id=bot_id, dialog_id=dialog_id)


@router.get("/dialogs/{dialog_id}/messages", response_model=ListResponse[DialogMessageOut])
async def list_messages(
    dialog_id: int,
    sender: MessageSender | None = None,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogMessagesService = Depends(DialogMessagesService),
    dialogs_service: DialogsService = Depends(DialogsService),
) -> ListResponse[DialogMessageOut]:
    validate_pagination(page, per_page)

    dialog = await dialogs_service.get(session=session, bot_id=None, dialog_id=dialog_id)
    if not dialog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found")
    items, total, has_next = await service.list(
        session=session, filters={"dialog_id": dialog_id, "sender": sender}, page=page, per_page=per_page
    )
    return ListResponse[DialogMessageOut](
        items=items,
        page=page,
        per_page=per_page,
        total=total,
        has_next=has_next,
    )


@router.websocket("/ws/admin")
async def ws_admin(websocket: WebSocket, token: str) -> None:
    try:
        payload = decode_access_token(token)
        admin_id = int(payload.get("sub"))
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.register_admin(admin_id=admin_id, ws=websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.unregister_admin(admin_id=admin_id, ws=websocket)


@router.websocket("/ws/webchat/{bot_id}/{session_id}")
async def ws_webchat(websocket: WebSocket, bot_id: int, session_id: str) -> None:
    await manager.register_webchat(bot_id=bot_id, session_id=session_id, ws=websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.unregister_webchat(bot_id=bot_id, session_id=session_id, ws=websocket)


@router.post(
    "/dialogs/{dialog_id}/messages",
    response_model=DialogMessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_dialog_message(
    dialog_id: int,
    data: OperatorMessageIn,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogsService = Depends(DialogsService),
) -> DialogMessageOut:
    dialog = await service.get(session=session, bot_id=None, dialog_id=dialog_id)
    if not dialog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found")
    if dialog.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dialog is closed")

    message, _updated_dialog, dialog_created = await service.add_message(
        session=session,
        bot_id=dialog.bot_id,
        channel_type=dialog.channel_type,
        external_chat_id=dialog.external_chat_id,
        external_user_id=dialog.external_user_id,
        sender=MessageSender.OPERATOR,
        text=data.text,
        payload=data.payload,
    )

    dialog_detail = await service.get(session=session, bot_id=None, dialog_id=dialog_id, include_messages=True)
    message_payload = DialogMessageOut.model_validate(message).model_dump()
    dialog_payload = DialogDetail.model_validate(
        dialog_detail, update={"messages": sorted(dialog_detail.messages, key=lambda m: m.created_at)}
    ).model_dump()

    admin_targets = _resolve_admin_targets(dialog_payload)

    if dialog_created:
        await manager.broadcast_to_admins({"event": "dialog_created", "data": dialog_payload}, admin_ids=admin_targets)
        await manager.broadcast_to_webchat(
            bot_id=dialog_payload["bot_id"],
            session_id=dialog_payload["external_chat_id"],
            message={"event": "dialog_created", "data": dialog_payload},
        )

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

    return DialogMessageOut.model_validate(message)
