"""Accounts and users API router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.modules.accounts.models import User
from app.modules.accounts.schemas import (
    AccountCreate,
    AccountOut,
    AccountUpdate,
    ListResponse,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.modules.accounts.service import AccountsService, UsersService
from app.security.auth import get_current_user

router = APIRouter(prefix="", tags=["accounts", "users"])


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: UsersService = Depends(UsersService),
) -> UserOut:
    return await service.create(session=session, obj_in=data)


@router.get("/users", response_model=ListResponse[UserOut])
async def list_users(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: UsersService = Depends(UsersService),
) -> ListResponse[UserOut]:
    items = await service.list(session=session)
    return ListResponse[UserOut](items=items)


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: UsersService = Depends(UsersService),
) -> UserOut:
    db_user = await service.get(session=session, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: UsersService = Depends(UsersService),
) -> UserOut:
    db_user = await service.get(session=session, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return await service.update(session=session, db_obj=db_user, obj_in=data)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: UsersService = Depends(UsersService),
) -> None:
    db_user = await service.get(session=session, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await service.delete(session=session, user_id=user_id)


@router.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(
    data: AccountCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: AccountsService = Depends(AccountsService),
) -> AccountOut:
    return await service.create(session=session, obj_in=data)


@router.get("/accounts", response_model=ListResponse[AccountOut])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: AccountsService = Depends(AccountsService),
) -> ListResponse[AccountOut]:
    items = await service.list(session=session)
    return ListResponse[AccountOut](items=items)


@router.get("/accounts/{account_id}", response_model=AccountOut)
async def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: AccountsService = Depends(AccountsService),
) -> AccountOut:
    db_account = await service.get(session=session, account_id=account_id)
    if not db_account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return db_account


@router.patch("/accounts/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: int,
    data: AccountUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: AccountsService = Depends(AccountsService),
) -> AccountOut:
    db_account = await service.get(session=session, account_id=account_id)
    if not db_account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return await service.update(session=session, db_obj=db_account, obj_in=data)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: AccountsService = Depends(AccountsService),
) -> None:
    db_account = await service.get(session=session, account_id=account_id)
    if not db_account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    await service.delete(session=session, account_id=account_id)
