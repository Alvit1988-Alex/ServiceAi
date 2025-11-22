"""Dialog service implementing CRUD operations."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dialogs.models import Dialog, DialogMessage
from app.modules.dialogs.schemas import DialogCreate, DialogMessageCreate, DialogUpdate


class DialogsService:
    model = Dialog

    async def create(self, session: AsyncSession, obj_in: DialogCreate) -> Dialog:
        db_obj = Dialog(
            bot_id=obj_in.bot_id,
            user_external_id=obj_in.user_external_id,
            status=obj_in.status,
            closed=obj_in.closed,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get(self, session: AsyncSession, bot_id: int | None, dialog_id: int) -> Dialog | None:
        stmt = select(Dialog).where(Dialog.id == dialog_id)
        if bot_id is not None:
            stmt = stmt.where(Dialog.bot_id == bot_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def list(self, session: AsyncSession, filters: dict[str, Any] | None = None) -> list[Dialog]:
        stmt = select(Dialog)
        if filters:
            for field, value in filters.items():
                if value is not None:
                    stmt = stmt.where(getattr(Dialog, field) == value)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update(self, session: AsyncSession, db_obj: Dialog, obj_in: DialogUpdate) -> Dialog:
        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(db_obj, field, value)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, session: AsyncSession, bot_id: int, dialog_id: int) -> None:
        obj = await self.get(session, bot_id, dialog_id)
        if obj:
            await session.delete(obj)
            await session.commit()


class DialogMessagesService:
    model = DialogMessage

    async def create(self, session: AsyncSession, obj_in: DialogMessageCreate) -> DialogMessage:
        db_obj = DialogMessage(
            dialog_id=obj_in.dialog_id,
            sender=obj_in.sender,
            text=obj_in.text,
            payload=obj_in.payload,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get(self, session: AsyncSession, message_id: int) -> DialogMessage | None:
        result = await session.execute(select(DialogMessage).where(DialogMessage.id == message_id))
        return result.scalars().first()

    async def list(self, session: AsyncSession, filters: dict[str, Any] | None = None) -> list[DialogMessage]:
        stmt = select(DialogMessage)
        if filters:
            for field, value in filters.items():
                if value is not None:
                    stmt = stmt.where(getattr(DialogMessage, field) == value)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def delete(self, session: AsyncSession, message_id: int) -> None:
        obj = await self.get(session, message_id)
        if obj:
            await session.delete(obj)
            await session.commit()
