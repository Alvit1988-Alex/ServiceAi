"""Bots API router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.modules.accounts.service import AccountsService
from app.modules.accounts.models import User
from app.modules.bots.schemas import BotCreate, BotCreateInternal, BotOut, BotUpdate, ListResponse
from app.modules.bots.service import BotsService
from app.security.auth import get_current_user

router = APIRouter(prefix="/bots", tags=["bots"])


@router.post("", response_model=BotOut, status_code=status.HTTP_201_CREATED)
async def create_bot(
    data: BotCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    accounts_service: AccountsService = Depends(AccountsService),
    service: BotsService = Depends(BotsService),
) -> BotOut:
    account = await accounts_service.get_or_create_for_owner(session=session, owner=current_user)
    bot_data = BotCreateInternal(**data.model_dump(), account_id=account.id)
    return await service.create(session=session, obj_in=bot_data)


@router.get("", response_model=ListResponse[BotOut])
async def list_bots(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: BotsService = Depends(BotsService),
) -> ListResponse[BotOut]:
    items = await service.list(session=session)
    return ListResponse[BotOut](items=items)


@router.get("/{bot_id}", response_model=BotOut)
async def get_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: BotsService = Depends(BotsService),
) -> BotOut:
    db_bot = await service.get(session=session, bot_id=bot_id)
    if not db_bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    return db_bot


@router.patch("/{bot_id}", response_model=BotOut)
async def update_bot(
    bot_id: int,
    data: BotUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: BotsService = Depends(BotsService),
) -> BotOut:
    db_bot = await service.get(session=session, bot_id=bot_id)
    if not db_bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    return await service.update(session=session, db_obj=db_bot, obj_in=data)


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: BotsService = Depends(BotsService),
) -> None:
    db_bot = await service.get(session=session, bot_id=bot_id)
    if not db_bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    await service.delete(session=session, bot_id=bot_id)
