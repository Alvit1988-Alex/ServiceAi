"""Bots CRUD service."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.modules.accounts.models import Account, User
from app.modules.bots.models import Bot, BotAdmin
from app.modules.bots.schemas import BotAdminCreate, BotAdminOut, BotCreateInternal, BotUpdate
from app.modules.channels.service import ChannelsService


class BotsService:
    model = Bot

    async def create(self, session: AsyncSession, obj_in: BotCreateInternal) -> Bot:
        channels_service = ChannelsService()

        try:
            db_obj = Bot(account_id=obj_in.account_id, name=obj_in.name, description=obj_in.description)
            session.add(db_obj)
            await session.flush()

            await channels_service.create_default_channels(session=session, bot_id=db_obj.id)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        await session.refresh(db_obj)
        return db_obj

    async def get(self, session: AsyncSession, bot_id: int) -> Bot | None:
        result = await session.execute(select(Bot).options(selectinload(Bot.account)).where(Bot.id == bot_id))
        return result.scalars().first()

    async def list(
        self,
        session: AsyncSession,
        filters: dict[str, Any] | None = None,
        extra_clauses: list[ColumnElement[bool]] | None = None,
    ) -> list[Bot]:
        stmt = select(Bot).options(selectinload(Bot.account))
        if filters:
            for field, value in filters.items():
                if value is not None:
                    stmt = stmt.where(getattr(Bot, field) == value)
        if extra_clauses:
            for clause in extra_clauses:
                stmt = stmt.where(clause)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update(self, session: AsyncSession, db_obj: Bot, obj_in: BotUpdate) -> Bot:
        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(db_obj, field, value)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, session: AsyncSession, bot_id: int) -> None:
        obj = await self.get(session, bot_id)
        if obj:
            await session.delete(obj)
            await session.commit()

    async def list_admins(self, session: AsyncSession, bot_id: int) -> list[BotAdminOut]:
        result = await session.execute(
            select(BotAdmin, User, Account)
            .join(User, User.id == BotAdmin.user_id)
            .join(Account, Account.owner_id == User.id)
            .where(BotAdmin.bot_id == bot_id)
            .order_by(BotAdmin.created_at.asc())
        )
        return [
            BotAdminOut(
                id=admin.id,
                bot_id=admin.bot_id,
                user_id=admin.user_id,
                role=admin.role,
                account_public_id=account.public_id,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            for admin, user, account in result.all()
        ]

    async def add_admin(self, session: AsyncSession, bot: Bot, data: BotAdminCreate) -> BotAdminOut:
        if not data.account_public_id.isdigit() or len(data.account_public_id) != 8:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account public id")

        current_count = await session.scalar(select(func.count(BotAdmin.id)).where(BotAdmin.bot_id == bot.id))
        if (current_count or 0) >= 10:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bot admins limit reached")

        account = await session.scalar(select(Account).where(Account.public_id == data.account_public_id))
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        if account.owner_id == bot.account.owner_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner has implicit access")

        existing = await session.scalar(
            select(BotAdmin.id).where(BotAdmin.bot_id == bot.id, BotAdmin.user_id == account.owner_id)
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin already exists")

        db_obj = BotAdmin(bot_id=bot.id, user_id=account.owner_id, role=data.role)
        session.add(db_obj)
        await session.commit()
        return (await self.list_admins(session=session, bot_id=bot.id))[-1]

    async def get_admin(self, session: AsyncSession, bot_id: int, user_id: int) -> BotAdmin | None:
        return await session.scalar(select(BotAdmin).where(BotAdmin.bot_id == bot_id, BotAdmin.user_id == user_id))

    async def remove_admin(self, session: AsyncSession, bot_id: int, user_id: int) -> None:
        admin = await self.get_admin(session=session, bot_id=bot_id, user_id=user_id)
        if admin:
            await session.delete(admin)
            await session.commit()
