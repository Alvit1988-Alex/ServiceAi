"""Bots CRUD service."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bots.models import Bot
from app.modules.bots.schemas import BotCreateInternal, BotUpdate
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
        result = await session.execute(select(Bot).where(Bot.id == bot_id))
        return result.scalars().first()

    async def list(
        self,
        session: AsyncSession,
        filters: dict[str, Any] | None = None,
        extra_clauses: list[ColumnElement[bool]] | None = None,
    ) -> list[Bot]:
        stmt = select(Bot)
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
