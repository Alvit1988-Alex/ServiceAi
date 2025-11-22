"""Service layer for account and user operations."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts.models import Account, User
from app.modules.accounts.schemas import AccountCreate, AccountUpdate, UserCreate, UserUpdate
from app.security.hashing import hash_password


class UsersService:
    model = User

    async def create(self, session: AsyncSession, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            password_hash=hash_password(obj_in.password),
            full_name=obj_in.full_name,
            role=obj_in.role,
            is_active=obj_in.is_active,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get(self, session: AsyncSession, user_id: int) -> User | None:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def list(self, session: AsyncSession, filters: dict[str, Any] | None = None) -> list[User]:
        stmt = select(User)
        if filters:
            for field, value in filters.items():
                if value is not None:
                    stmt = stmt.where(getattr(User, field) == value)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update(self, session: AsyncSession, db_obj: User, obj_in: UserUpdate) -> User:
        data = obj_in.model_dump(exclude_unset=True)
        if "password" in data:
            db_obj.password_hash = hash_password(data.pop("password"))
        for field, value in data.items():
            setattr(db_obj, field, value)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, session: AsyncSession, user_id: int) -> None:
        obj = await self.get(session, user_id)
        if obj:
            await session.delete(obj)
            await session.commit()


class AccountsService:
    model = Account

    async def _load_operators(self, session: AsyncSession, operator_ids: list[int] | None) -> list[User]:
        if not operator_ids:
            return []
        result = await session.execute(select(User).where(User.id.in_(operator_ids)))
        return result.scalars().all()

    async def create(self, session: AsyncSession, obj_in: AccountCreate) -> Account:
        operators = await self._load_operators(session, obj_in.operator_ids)
        db_obj = Account(name=obj_in.name, owner_id=obj_in.owner_id, operators=operators)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get(self, session: AsyncSession, account_id: int) -> Account | None:
        result = await session.execute(select(Account).where(Account.id == account_id))
        return result.scalars().first()

    async def list(self, session: AsyncSession, filters: dict[str, Any] | None = None) -> list[Account]:
        stmt = select(Account)
        if filters:
            for field, value in filters.items():
                if value is not None:
                    stmt = stmt.where(getattr(Account, field) == value)
        result = await session.execute(stmt)
        return result.scalars().unique().all()

    async def update(self, session: AsyncSession, db_obj: Account, obj_in: AccountUpdate) -> Account:
        data = obj_in.model_dump(exclude_unset=True)
        operator_ids = data.pop("operator_ids", None)
        if operator_ids is not None:
            db_obj.operators = await self._load_operators(session, operator_ids)
        for field, value in data.items():
            setattr(db_obj, field, value)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, session: AsyncSession, account_id: int) -> None:
        obj = await self.get(session, account_id)
        if obj:
            await session.delete(obj)
            await session.commit()
