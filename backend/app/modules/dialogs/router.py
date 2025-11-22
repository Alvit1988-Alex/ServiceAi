"""Dialogs API router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.modules.accounts.models import User
from app.modules.dialogs.schemas import DialogMessageOut, DialogOut, ListResponse
from app.modules.dialogs.service import DialogMessagesService, DialogsService
from app.security.auth import get_current_user

router = APIRouter(tags=["dialogs"])


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
