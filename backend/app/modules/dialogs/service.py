"""Dialog service implementing CRUD operations."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.ai.service import AIService
from app.modules.channels.models import ChannelType
from app.modules.channels.schemas import NormalizedIncomingMessage
from app.modules.channels.sender_registry import get_sender
from app.modules.dialogs.models import Dialog, DialogMessage, DialogStatus, MessageSender
from app.modules.dialogs.schemas import DialogCreate, DialogMessageCreate, DialogUpdate
from app.utils.validators import validate_pagination


class DialogLockError(Exception):
    """Raised when a dialog lock or unlock operation cannot be completed."""


class DialogsService:
    model = Dialog

    async def create(self, session: AsyncSession, obj_in: DialogCreate) -> Dialog:
        db_obj = Dialog(
            bot_id=obj_in.bot_id,
            channel_type=obj_in.channel_type,
            external_chat_id=obj_in.external_chat_id,
            external_user_id=obj_in.external_user_id,
            status=obj_in.status,
            closed=obj_in.closed,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get(
        self, session: AsyncSession, bot_id: int | None, dialog_id: int, include_messages: bool = False
    ) -> Dialog | None:
        stmt = select(Dialog).where(Dialog.id == dialog_id)
        if bot_id is not None:
            stmt = stmt.where(Dialog.bot_id == bot_id)
        if include_messages:
            stmt = stmt.options(selectinload(Dialog.messages).order_by(DialogMessage.created_at.asc()))
        result = await session.execute(stmt)
        return result.scalars().unique().first()

    async def get_or_create_dialog(
        self,
        session: AsyncSession,
        bot_id: int,
        channel_type: ChannelType,
        external_chat_id: str,
        external_user_id: str | None = None,
    ) -> tuple[Dialog, bool]:
        stmt = (
            select(Dialog)
            .where(
                Dialog.bot_id == bot_id,
                Dialog.channel_type == channel_type,
                Dialog.external_chat_id == external_chat_id,
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
            channel_type=channel_type,
            external_chat_id=external_chat_id,
            external_user_id=external_user_id or external_chat_id,
            status=DialogStatus.AUTO,
            closed=False,
        )
        session.add(dialog)
        await session.commit()
        await session.refresh(dialog)
        return dialog, True

    async def list(
        self,
        session: AsyncSession,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        per_page: int = 20,
        include_messages: bool = False,
    ) -> tuple[list[Dialog], int, bool]:
        validate_pagination(page, per_page)

        conditions: list[Any] = []
        if filters:
            for field, value in filters.items():
                if value is not None:
                    conditions.append(getattr(Dialog, field) == value)

        stmt = select(Dialog).where(*conditions).order_by(Dialog.updated_at.desc())
        if include_messages:
            stmt = stmt.options(selectinload(Dialog.messages).order_by(DialogMessage.created_at.asc()))

        total_result = await session.execute(
            select(func.count()).select_from(select(Dialog.id).where(*conditions).subquery())
        )
        total = total_result.scalar_one()

        result = await session.execute(stmt.offset((page - 1) * per_page).limit(per_page))
        items = result.scalars().unique().all()
        has_next = page * per_page < total
        return items, total, has_next

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

    async def lock_dialog(self, session: AsyncSession, dialog: Dialog, admin_id: int) -> Dialog:
        if dialog.assigned_admin_id not in (None, admin_id):
            raise DialogLockError("Dialog is assigned to another operator")

        if dialog.is_locked and dialog.assigned_admin_id != admin_id:
            raise DialogLockError("Dialog is already locked by another operator")

        dialog.is_locked = True
        dialog.assigned_admin_id = admin_id
        dialog.locked_until = None
        dialog.updated_at = datetime.utcnow()

        session.add(dialog)
        await session.commit()
        await session.refresh(dialog)
        return dialog

    async def unlock_dialog(self, session: AsyncSession, dialog: Dialog, admin_id: int) -> Dialog:
        if dialog.assigned_admin_id not in (None, admin_id):
            raise DialogLockError("Dialog is locked by another operator")

        dialog.is_locked = False
        dialog.locked_until = None
        dialog.assigned_admin_id = None
        dialog.updated_at = datetime.utcnow()

        session.add(dialog)
        await session.commit()
        await session.refresh(dialog)
        return dialog

    async def add_message(
        self,
        session: AsyncSession,
        bot_id: int,
        channel_type: ChannelType,
        external_chat_id: str,
        external_user_id: str,
        sender: MessageSender,
        text: str | None = None,
        payload: dict | None = None,
    ) -> tuple[DialogMessage, Dialog, bool]:
        dialog, dialog_created = await self.get_or_create_dialog(
            session=session,
            bot_id=bot_id,
            channel_type=channel_type,
            external_chat_id=external_chat_id,
            external_user_id=external_user_id,
        )

        now = datetime.utcnow()

        dialog.closed = False
        if sender == MessageSender.USER:
            dialog.status = DialogStatus.WAIT_OPERATOR
            dialog.last_user_message_at = now
            dialog.waiting_time_seconds = 0
            dialog.unread_messages_count += 1
        else:
            dialog.status = DialogStatus.WAIT_USER
            dialog.waiting_time_seconds = (
                int((now - dialog.last_user_message_at).total_seconds())
                if dialog.last_user_message_at
                else 0
            )
            dialog.unread_messages_count = 0
        dialog.updated_at = now
        dialog.last_message_at = now

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
            channel_type=incoming_message.channel_type,
            external_chat_id=incoming_message.external_chat_id,
            external_user_id=incoming_message.external_user_id,
        )

        now = datetime.utcnow()

        dialog.closed = False
        dialog.status = DialogStatus.WAIT_OPERATOR
        dialog.updated_at = now
        dialog.last_message_at = now
        dialog.last_user_message_at = now
        dialog.waiting_time_seconds = 0
        dialog.unread_messages_count += 1

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

            bot_response_time_seconds = (
                int((datetime.utcnow() - dialog.last_user_message_at).total_seconds())
                if dialog.last_user_message_at
                else 0
            )
            dialog.status = DialogStatus.WAIT_USER
            dialog.updated_at = datetime.utcnow()
            dialog.last_message_at = datetime.utcnow()
            dialog.waiting_time_seconds = bot_response_time_seconds
            dialog.unread_messages_count = 0

            session.add_all([dialog, bot_message])
            await session.commit()
            await session.refresh(dialog)
            await session.refresh(bot_message)

            sender_cls = get_sender(incoming_message.channel_type)
            await sender_cls().send_text(
                bot_id=incoming_message.bot_id,
                external_chat_id=incoming_message.external_chat_id,
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

    async def list(
        self,
        session: AsyncSession,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[DialogMessage], int, bool]:
        validate_pagination(page, per_page)

        conditions: list[Any] = []
        if filters:
            for field, value in filters.items():
                if value is not None:
                    conditions.append(getattr(DialogMessage, field) == value)

        stmt = select(DialogMessage).where(*conditions).order_by(DialogMessage.created_at.asc())
        total_result = await session.execute(
            select(func.count()).select_from(select(DialogMessage.id).where(*conditions).subquery())
        )
        total = total_result.scalar_one()

        result = await session.execute(stmt.offset((page - 1) * per_page).limit(per_page))
        items = result.scalars().all()
        has_next = page * per_page < total
        return items, total, has_next

    async def delete(self, session: AsyncSession, message_id: int) -> None:
        obj = await self.get(session, message_id)
        if obj:
            await session.delete(obj)
            await session.commit()
