"""Dialogs API router."""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.modules.accounts.models import User
from app.modules.dialogs.models import MessageSender
from app.modules.dialogs.schemas import DialogMessageOut, DialogOut, ListResponse
from app.modules.dialogs.service import DialogMessagesService, DialogsService
from app.modules.dialogs.websocket_manager import manager
from app.security.auth import get_current_user
from app.security.jwt import decode_access_token

router = APIRouter(tags=["dialogs"])


class OperatorMessageIn(BaseModel):
    text: str | None = None
    payload: dict | None = None


@router.get("/bots/{bot_id}/dialogs", response_model=ListResponse[DialogOut])
async def list_dialogs(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogsService = Depends(DialogsService),
) -> ListResponse[DialogOut]:
    items = await service.list(session=session, filters={"bot_id": bot_id})
    return ListResponse[DialogOut](items=items)


@router.get("/bots/{bot_id}/dialogs/{dialog_id}", response_model=DialogOut)
async def get_dialog(
    bot_id: int,
    dialog_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogsService = Depends(DialogsService),
) -> DialogOut:
    dialog = await service.get(session=session, bot_id=bot_id, dialog_id=dialog_id)
    if not dialog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found")
    return dialog


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
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: DialogMessagesService = Depends(DialogMessagesService),
    dialogs_service: DialogsService = Depends(DialogsService),
) -> ListResponse[DialogMessageOut]:
    dialog = await dialogs_service.get(session=session, bot_id=None, dialog_id=dialog_id)
    if not dialog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found")
    items = await service.list(session=session, filters={"dialog_id": dialog_id})
    return ListResponse[DialogMessageOut](items=items)


@router.websocket("/ws/admin")
async def ws_admin(websocket: WebSocket, token: str) -> None:
    try:
        decode_access_token(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_admin(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_admin(websocket)


@router.websocket("/ws/webchat/{bot_id}/{session_id}")
async def ws_webchat(websocket: WebSocket, bot_id: int, session_id: str) -> None:
    await manager.connect_webchat(bot_id=bot_id, session_id=session_id, ws=websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_webchat(bot_id=bot_id, session_id=session_id, ws=websocket)


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

    message, updated_dialog, dialog_created = await service.add_message(
        session=session,
        bot_id=dialog.bot_id,
        user_external_id=dialog.user_external_id,
        sender=MessageSender.OPERATOR,
        text=data.text,
        payload=data.payload,
    )

    message_payload = DialogMessageOut.model_validate(message).model_dump()
    dialog_payload = DialogOut.model_validate(updated_dialog).model_dump()

    if dialog_created:
        await manager.broadcast_to_admins({"event": "dialog_created", "data": dialog_payload})
        await manager.broadcast_to_webchat(
            bot_id=dialog_payload["bot_id"],
            session_id=dialog_payload["user_external_id"],
            message={"event": "dialog_created", "data": dialog_payload},
        )

    await manager.broadcast_to_admins({"event": "message_created", "data": message_payload})
    await manager.broadcast_to_admins({"event": "dialog_updated", "data": dialog_payload})

    await manager.broadcast_to_webchat(
        bot_id=dialog_payload["bot_id"],
        session_id=dialog_payload["user_external_id"],
        message={"event": "message_created", "data": message_payload},
    )
    await manager.broadcast_to_webchat(
        bot_id=dialog_payload["bot_id"],
        session_id=dialog_payload["user_external_id"],
        message={"event": "dialog_updated", "data": dialog_payload},
    )

    return DialogMessageOut.model_validate(message)
