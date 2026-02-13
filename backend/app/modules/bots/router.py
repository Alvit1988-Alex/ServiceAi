"""Bots API router."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_accessible_account_ids, get_accessible_bot, get_db_session
from app.modules.accounts.service import AccountsService
from app.modules.accounts.models import User, UserRole
from app.modules.bots.models import Bot
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
    if current_user.role == UserRole.admin:
        items = await service.list(session=session)
    else:
        account_ids = await get_accessible_account_ids(session=session, user=current_user)
        if not account_ids:
            items = []
        else:
            items = await service.list(session=session, extra_clauses=[Bot.account_id.in_(account_ids)])
    return ListResponse[BotOut](items=items)


@router.get("/{bot_id}", response_model=BotOut)
async def get_bot(
    accessible_bot: Bot = Depends(get_accessible_bot),
) -> BotOut:
    return accessible_bot


@router.patch("/{bot_id}", response_model=BotOut)
async def update_bot(
    data: BotUpdate,
    accessible_bot: Bot = Depends(get_accessible_bot),
    session: AsyncSession = Depends(get_db_session),
    service: BotsService = Depends(BotsService),
) -> BotOut:
    return await service.update(session=session, db_obj=accessible_bot, obj_in=data)


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    accessible_bot: Bot = Depends(get_accessible_bot),
    session: AsyncSession = Depends(get_db_session),
    service: BotsService = Depends(BotsService),
) -> None:
    await service.delete(session=session, bot_id=accessible_bot.id)
