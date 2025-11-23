"""Dialog service implementing CRUD operations."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.service import AIService
from app.modules.channels.schemas import NormalizedIncomingMessage
from app.modules.channels.sender_registry import get_sender
from app.modules.dialogs.models import Dialog, DialogMessage, DialogStatus, MessageSender
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

    async def get_or_create_dialog(
        self, session: AsyncSession, bot_id: int, user_external_id: str
    ) -> tuple[Dialog, bool]:
        stmt = (
            select(Dialog)
            .where(
                Dialog.bot_id == bot_id,
                Dialog.user_external_id == user_external_id,
                Dialog.closed.is_(False),
            )
            .order_by(Dialog.updated_at.desc())
        )
        result = await session.execute(stmt)
        dialog = result.scalars().first()
        if dialog:
            return dialog, False

        dialog = Dialog(
            bot_id=bot_id,
            user_external_id=user_external_id,
            status=DialogStatus.AUTO,
            closed=False,
        )
        session.add(dialog)
        await session.commit()
        await session.refresh(dialog)
        return dialog, True

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

    async def close_dialog(self, session: AsyncSession, dialog: Dialog) -> Dialog:
        dialog.closed = True
        dialog.updated_at = datetime.utcnow()

        session.add(dialog)
        await session.commit()
        await session.refresh(dialog)
        return dialog

    async def add_message(
        self,
        session: AsyncSession,
        bot_id: int,
        user_external_id: str,
        sender: MessageSender,
        text: str | None = None,
        payload: dict | None = None,
    ) -> tuple[DialogMessage, Dialog, bool]:
        dialog, dialog_created = await self.get_or_create_dialog(
            session=session, bot_id=bot_id, user_external_id=user_external_id
        )

        dialog.closed = False
        if sender == MessageSender.USER:
            dialog.status = DialogStatus.WAIT_OPERATOR
        else:
            dialog.status = DialogStatus.WAIT_USER
        dialog.updated_at = datetime.utcnow()

        message = DialogMessage(
            dialog_id=dialog.id,
            sender=sender,
            text=text,
            payload=payload,
        )
        session.add_all([dialog, message])
        await session.commit()
        await session.refresh(dialog)
        await session.refresh(message)
        return message, dialog, dialog_created

    async def delete(self, session: AsyncSession, bot_id: int, dialog_id: int) -> None:
        obj = await self.get(session, bot_id, dialog_id)
        if obj:
            await session.delete(obj)
            await session.commit()

    async def process_incoming_message(
        self,
        session: AsyncSession,
        incoming_message: NormalizedIncomingMessage,
        ai_service: AIService,
    ) -> tuple[DialogMessage, DialogMessage | None, Dialog, bool]:
        dialog, dialog_created = await self.get_or_create_dialog(
            session=session,
            bot_id=incoming_message.bot_id,
            user_external_id=incoming_message.external_user_id,
        )

        dialog.closed = False
        dialog.status = DialogStatus.WAIT_OPERATOR
        dialog.updated_at = datetime.utcnow()

        user_message = DialogMessage(
            dialog_id=dialog.id,
            sender=MessageSender.USER,
            text=incoming_message.text,
            payload=incoming_message.payload,
        )
        session.add_all([dialog, user_message])
        await session.commit()
        await session.refresh(dialog)
        await session.refresh(user_message)

        bot_message: DialogMessage | None = None
        answer = await ai_service.answer(
            bot_id=incoming_message.bot_id,
            dialog_id=dialog.id,
            question=incoming_message.text or "",
        )

        if answer.can_answer and answer.answer:
            bot_message = DialogMessage(
                dialog_id=dialog.id,
                sender=MessageSender.BOT,
                text=answer.answer,
            )

            dialog.status = DialogStatus.WAIT_USER
            dialog.updated_at = datetime.utcnow()

            session.add_all([dialog, bot_message])
            await session.commit()
            await session.refresh(dialog)
            await session.refresh(bot_message)

            sender_cls = get_sender(incoming_message.channel_type)
            await sender_cls().send_text(
                bot_id=incoming_message.bot_id,
                external_chat_id=incoming_message.external_user_id,
                text=answer.answer,
            )
        else:
            dialog.status = DialogStatus.WAIT_OPERATOR
            dialog.updated_at = datetime.utcnow()
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)

        return user_message, bot_message, dialog, dialog_created


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
