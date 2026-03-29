"""Bots API router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_accessible_account_ids,
    get_bot_access_role,
    get_bot_for_settings_read,
    get_bot_owner_only,
    get_db_session,
    require_owner_or_superadmin,
)
from app.modules.accounts.models import User, UserRole
from app.modules.accounts.service import AccountsService
from app.modules.bots.models import Bot, BotAdminRole
from app.modules.bots.schemas import (
    BotAdminCreate,
    BotAdminDelete,
    BotAdminOut,
    BotCreate,
    BotCreateInternal,
    BotOut,
    BotUpdate,
    ListResponse,
)
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
    created = await service.create(session=session, obj_in=bot_data)
    return BotOut.model_validate(created).model_copy(update={"is_owned": True, "access_role": "owner"})


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

    output: list[BotOut] = []
    for bot in items:
        role = await get_bot_access_role(session=session, user=current_user, bot=bot)
        if role is None and current_user.role != UserRole.admin:
            continue
        output.append(
            BotOut.model_validate(bot).model_copy(
                update={
                    "is_owned": bot.account.owner_id == current_user.id,
                    "access_role": "owner" if bot.account.owner_id == current_user.id else (role or "owner"),
                }
            )
        )

    return ListResponse[BotOut](items=output)


@router.get("/{bot_id}", response_model=BotOut)
async def get_bot(
    accessible_bot: Bot = Depends(get_bot_for_settings_read),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> BotOut:
    role = await get_bot_access_role(session=session, user=current_user, bot=accessible_bot)
    return BotOut.model_validate(accessible_bot).model_copy(
        update={"is_owned": accessible_bot.account.owner_id == current_user.id, "access_role": role or "owner"}
    )


@router.patch("/{bot_id}", response_model=BotOut)
async def update_bot(
    data: BotUpdate,
    accessible_bot: Bot = Depends(get_bot_owner_only),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: BotsService = Depends(BotsService),
) -> BotOut:
    updated = await service.update(session=session, db_obj=accessible_bot, obj_in=data)
    return BotOut.model_validate(updated).model_copy(update={"is_owned": True, "access_role": "owner"})


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    accessible_bot: Bot = Depends(get_bot_owner_only),
    session: AsyncSession = Depends(get_db_session),
    service: BotsService = Depends(BotsService),
) -> None:
    await service.delete(session=session, bot_id=accessible_bot.id)


@router.get("/{bot_id}/admins", response_model=ListResponse[BotAdminOut])
async def list_bot_admins(
    access: tuple[Bot, str, User] = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session),
    service: BotsService = Depends(BotsService),
) -> ListResponse[BotAdminOut]:
    bot, _role, _user = access
    return ListResponse[BotAdminOut](items=await service.list_admins(session=session, bot_id=bot.id))


@router.post("/{bot_id}/admins", response_model=BotAdminOut, status_code=status.HTTP_201_CREATED)
async def add_bot_admin(
    data: BotAdminCreate,
    access: tuple[Bot, str, User] = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session),
    service: BotsService = Depends(BotsService),
) -> BotAdminOut:
    bot, role, _user = access
    if role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can add admins")
    return await service.add_admin(session=session, bot=bot, data=data)


@router.delete("/{bot_id}/admins", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bot_admin(
    data: BotAdminDelete,
    access: tuple[Bot, str, User] = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session),
    service: BotsService = Depends(BotsService),
) -> None:
    bot, role, current_user = access
    if data.user_id == bot.account.owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner cannot be removed")

    target = await service.get_admin(session=session, bot_id=bot.id, user_id=data.user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    if role == "superadmin" and target.role != BotAdminRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    if role == "superadmin" and target.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot remove yourself")

    await service.remove_admin(session=session, bot_id=bot.id, user_id=data.user_id)
