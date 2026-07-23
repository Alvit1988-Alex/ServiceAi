"""Dialog service implementing CRUD operations."""
from __future__ import annotations

import asyncio
import logging
import unicodedata
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.ai.service import AIService
from app.modules.accounts.models import Account, User, UserRole, account_operators
from app.modules.bots.models import Bot, BotAdmin
from app.modules.channels.models import ChannelType
from app.modules.channels.schemas import NormalizedIncomingMessage
from app.modules.channels.sender_registry import get_sender
from app.modules.dialogs.models import Dialog, DialogMessage, DialogStatus, MessageSender, normalize_dialog_status
from app.modules.dialogs.schemas import (
    DialogCreate,
    DialogMessageCreate,
    DialogUpdate,
)
from app.modules.integrations.bitrix24.service import Bitrix24Service
from app.utils.validators import validate_pagination

logger = logging.getLogger(__name__)
AI_FALLBACK_TEXT = "Сейчас ИИ временно недоступен. Сообщение передано оператору — мы ответим как можно скорее."
HANDOFF_TEXT = "Передаю ваш вопрос оператору. Мы ответим как можно скорее."
AI_CANNOT_ANSWER_TEXT = "К сожалению, сейчас я не могу ответить на этот вопрос."


def _normalize_handoff_text(value: str) -> str:
    chars: list[str] = []
    for char in value.casefold():
        if char.isspace() or unicodedata.category(char).startswith("P"):
            chars.append(" ")
        else:
            chars.append(char)
    return " ".join("".join(chars).split())


def _matches_operator_trigger(message: str, phrases: list[str]) -> bool:
    normalized_message = _normalize_handoff_text(message)
    if not normalized_message:
        return False
    return any(phrase and _normalize_handoff_text(phrase) in normalized_message for phrase in phrases)


class DialogLockError(Exception):
    """Raised when a dialog lock or unlock operation cannot be completed."""


class DialogsService:
    model = Dialog


    async def count_waiting_operator_dialogs(self, session: AsyncSession, current_user: User) -> int:
        conditions: list[Any] = [
            Dialog.status == DialogStatus.WAIT_OPERATOR,
            Dialog.closed.is_(False),
            Dialog.assigned_admin_id.is_(None),
        ]

        stmt = select(func.count(func.distinct(Dialog.id))).select_from(Dialog).join(Bot, Bot.id == Dialog.bot_id)

        if current_user.role != UserRole.admin:
            stmt = stmt.join(Account, Account.id == Bot.account_id).outerjoin(
                BotAdmin,
                (BotAdmin.bot_id == Bot.id) & (BotAdmin.user_id == current_user.id),
            ).outerjoin(
                account_operators,
                (account_operators.c.account_id == Bot.account_id)
                & (account_operators.c.user_id == current_user.id),
            )
            conditions.append(
                or_(
                    Account.owner_id == current_user.id,
                    BotAdmin.user_id == current_user.id,
                    account_operators.c.user_id == current_user.id,
                )
            )

        result = await session.execute(stmt.where(*conditions))
        return int(result.scalar_one() or 0)

    async def _get_bot(self, session: AsyncSession, bot_id: int) -> Bot:
        bot = await session.scalar(select(Bot).where(Bot.id == bot_id))
        if bot is None:
            raise ValueError("Bot not found")
        return bot

    async def _save_and_send_bot_message(
        self,
        *,
        session: AsyncSession,
        dialog: Dialog,
        bot_id: int,
        channel_type: ChannelType,
        external_chat_id: str,
        text: str,
        status: DialogStatus,
        system: bool = False,
    ) -> DialogMessage:
        dialog.status = status
        dialog.updated_at = datetime.utcnow()
        dialog.last_message_at = datetime.utcnow()
        if status == DialogStatus.WAIT_USER:
            dialog.waiting_time_seconds = (
                int((datetime.utcnow() - dialog.last_user_message_at).total_seconds()) if dialog.last_user_message_at else 0
            )
            dialog.unread_messages_count = 0

        message = DialogMessage(
            dialog_id=dialog.id,
            sender=MessageSender.BOT,
            text=text,
            payload={"system": True} if system else None,
        )
        session.add_all([dialog, message])
        await session.commit()
        await session.refresh(dialog)
        await session.refresh(message)

        try:
            sender_cls = get_sender(channel_type)
            await sender_cls().send_text(bot_id=bot_id, external_chat_id=external_chat_id, text=text)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Bot message send failed",
                extra={"bot_id": bot_id, "dialog_id": dialog.id, "channel_type": channel_type},
            )
        return message

    async def _handoff_to_operator(
        self,
        *,
        session: AsyncSession,
        dialog: Dialog,
        bot_id: int,
        channel_type: ChannelType,
        external_chat_id: str,
    ) -> DialogMessage:
        return await self._save_and_send_bot_message(
            session=session,
            dialog=dialog,
            bot_id=bot_id,
            channel_type=channel_type,
            external_chat_id=external_chat_id,
            text=HANDOFF_TEXT,
            status=DialogStatus.WAIT_OPERATOR,
            system=True,
        )

    async def _cannot_answer(
        self,
        *,
        session: AsyncSession,
        dialog: Dialog,
        bot_id: int,
        channel_type: ChannelType,
        external_chat_id: str,
    ) -> DialogMessage:
        return await self._save_and_send_bot_message(
            session=session,
            dialog=dialog,
            bot_id=bot_id,
            channel_type=channel_type,
            external_chat_id=external_chat_id,
            text=AI_CANNOT_ANSWER_TEXT,
            status=DialogStatus.WAIT_USER,
        )

    async def create(self, session: AsyncSession, obj_in: DialogCreate) -> Dialog:
        db_obj = Dialog(
            bot_id=obj_in.bot_id,
            channel_type=obj_in.channel_type,
            external_chat_id=obj_in.external_chat_id,
            external_user_id=obj_in.external_user_id,
            status=normalize_dialog_status(obj_in.status),
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
        stmt = stmt.options(selectinload(Dialog.assigned_admin))
        if include_messages:
            # Keep eager loading simple; message ordering is handled when serializing the response.
            stmt = stmt.options(selectinload(Dialog.messages).selectinload(DialogMessage.operator_admin))
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
        locked_bot = await session.scalar(select(Bot).where(Bot.id == bot_id).with_for_update())
        if locked_bot is None:
            raise ValueError("Bot not found")

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
        stmt = stmt.options(selectinload(Dialog.assigned_admin))
        if include_messages:
            # Keep eager loading simple; message ordering is handled when serializing the response.
            stmt = stmt.options(selectinload(Dialog.messages).selectinload(DialogMessage.operator_admin))

        total_result = await session.execute(
            select(func.count()).select_from(select(Dialog.id).where(*conditions).subquery())
        )
        total = total_result.scalar_one()

        result = await session.execute(stmt.offset((page - 1) * per_page).limit(per_page))
        items = result.scalars().unique().all()
        has_next = page * per_page < total
        return items, total, has_next

    async def search_dialogs(
        self,
        session: AsyncSession,
        bot_id: int,
        query: str | None = None,
        status: DialogStatus | None = None,
        assigned_admin_id: int | None = None,
        channel_type: ChannelType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Dialog], int, bool]:
        validate_pagination(1, limit)
        if offset < 0:
            raise ValueError("offset must be >= 0")

        conditions: list[Any] = [Dialog.bot_id == bot_id]
        if status is not None:
            conditions.append(Dialog.status == status)
        if assigned_admin_id is not None:
            conditions.append(Dialog.assigned_admin_id == assigned_admin_id)
        if channel_type is not None:
            conditions.append(Dialog.channel_type == channel_type)

        search_expr = None
        if query:
            pattern = f"%{query}%"
            search_expr = or_(
                DialogMessage.text.ilike(pattern),
                Dialog.external_user_id.ilike(pattern),
                Dialog.external_chat_id.ilike(pattern),
            )

        stmt = select(Dialog).where(*conditions)
        count_stmt = select(func.count(func.distinct(Dialog.id))).select_from(Dialog).where(*conditions)

        if search_expr is not None:
            stmt = stmt.join(DialogMessage, DialogMessage.dialog_id == Dialog.id, isouter=True).where(search_expr)
            count_stmt = count_stmt.join(DialogMessage, DialogMessage.dialog_id == Dialog.id, isouter=True).where(
                search_expr
            )

        stmt = stmt.order_by(Dialog.last_message_at.desc()).offset(offset).limit(limit)
        stmt = stmt.options(selectinload(Dialog.assigned_admin))

        result = await session.execute(stmt)
        dialogs = result.scalars().unique().all()

        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()
        has_next = offset + limit < total

        return dialogs, total, has_next

    async def list_operator_dialogs(
        self,
        session: AsyncSession,
        bot_id: int,
        operator_id: int,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Dialog], int, bool]:
        validate_pagination(page, per_page)
        operator_dialog_ids = (
            select(DialogMessage.dialog_id)
            .where(
                DialogMessage.sender == MessageSender.OPERATOR,
                DialogMessage.operator_admin_id == operator_id,
            )
            .distinct()
        )
        conditions = [Dialog.bot_id == bot_id, Dialog.id.in_(operator_dialog_ids)]
        stmt = (
            select(Dialog)
            .where(*conditions)
            .order_by(Dialog.last_message_at.desc())
            .options(selectinload(Dialog.assigned_admin))
        )
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
            if field == "status" and value is not None:
                value = normalize_dialog_status(value)
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

    async def unlock_if_expired(self, session: AsyncSession, dialog: Dialog) -> tuple[Dialog, bool]:
        """Unlock a dialog when its lock has expired."""

        if dialog.is_locked and dialog.locked_until and dialog.locked_until < datetime.utcnow():
            admin_id = dialog.assigned_admin_id if dialog.assigned_admin_id is not None else 0
            unlocked_dialog = await self.unlock_dialog(session=session, dialog=dialog, admin_id=admin_id)
            return unlocked_dialog, True

        return dialog, False

    async def switch_to_auto(
        self,
        *,
        session: AsyncSession,
        dialog: Dialog,
        admin_id: int,
    ) -> Dialog:
        if dialog.assigned_admin_id not in (None, admin_id):
            raise DialogLockError("Dialog is locked by another operator")

        if dialog.closed:
            locked_bot = await session.scalar(select(Bot).where(Bot.id == dialog.bot_id).with_for_update())
            if locked_bot is None:
                raise ValueError("Bot not found")

            existing_open_dialog = await session.scalar(
                select(Dialog).where(
                    Dialog.id != dialog.id,
                    Dialog.bot_id == dialog.bot_id,
                    Dialog.channel_type == dialog.channel_type,
                    Dialog.external_chat_id == dialog.external_chat_id,
                    Dialog.closed.is_(False),
                )
            )
            if existing_open_dialog is not None:
                raise DialogLockError("Для этого чата уже существует активный диалог")

        dialog.status = DialogStatus.AUTO
        dialog.closed = False
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
        operator_admin_id: int | None = None,
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
                int((now - dialog.last_user_message_at).total_seconds()) if dialog.last_user_message_at else 0
            )
            dialog.unread_messages_count = 0
        dialog.updated_at = now
        dialog.last_message_at = now

        message = DialogMessage(
            dialog_id=dialog.id,
            sender=sender,
            text=text,
            payload=payload,
            operator_admin_id=operator_admin_id if sender == MessageSender.OPERATOR else None,
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

        dialog, _ = await self.unlock_if_expired(session=session, dialog=dialog)

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

        bitrix_service = Bitrix24Service()
        try:
            asyncio.create_task(
                bitrix_service.sync_incoming_user_message(
                    bot_id=incoming_message.bot_id,
                    dialog_id=dialog.id,
                    text=incoming_message.text,
                    dialog_created=dialog_created,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Bitrix24 sync scheduling failed",
                extra={"bot_id": incoming_message.bot_id, "dialog_id": dialog.id, "error": str(exc)},
            )

        if dialog.assigned_admin_id is not None and dialog.locked_until is not None and dialog.locked_until > now:
            return user_message, None, dialog, dialog_created

        bot = await self._get_bot(session=session, bot_id=incoming_message.bot_id)
        if bot.operator_handoff_enabled and _matches_operator_trigger(
            incoming_message.text or "", bot.operator_trigger_phrases
        ):
            system_message = await self._handoff_to_operator(
                session=session,
                dialog=dialog,
                bot_id=incoming_message.bot_id,
                channel_type=incoming_message.channel_type,
                external_chat_id=incoming_message.external_chat_id,
            )
            return user_message, system_message, dialog, dialog_created

        bot_message: DialogMessage | None = None
        try:
            answer = await ai_service.answer(
                bot_id=incoming_message.bot_id,
                dialog_id=dialog.id,
                question=incoming_message.text or "",
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "AI answer failed",
                extra={"bot_id": incoming_message.bot_id, "dialog_id": dialog.id},
            )
            answer = None

        if answer is None or not answer.can_answer or not answer.answer:
            system_message = await (
                self._handoff_to_operator(
                    session=session,
                    dialog=dialog,
                    bot_id=incoming_message.bot_id,
                    channel_type=incoming_message.channel_type,
                    external_chat_id=incoming_message.external_chat_id,
                )
                if bot.operator_handoff_enabled
                else self._cannot_answer(
                    session=session,
                    dialog=dialog,
                    bot_id=incoming_message.bot_id,
                    channel_type=incoming_message.channel_type,
                    external_chat_id=incoming_message.external_chat_id,
                )
            )
            return user_message, system_message, dialog, dialog_created

        if answer.can_answer and answer.answer:
            bot_message = DialogMessage(
                dialog_id=dialog.id,
                sender=MessageSender.BOT,
                text=answer.answer,
            )

            bot_response_time_seconds = (
                int((datetime.utcnow() - dialog.last_user_message_at).total_seconds()) if dialog.last_user_message_at else 0
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

    async def get_last_messages_map(
        self,
        session: AsyncSession,
        dialog_ids: list[int],
    ) -> dict[int, DialogMessage]:
        if not dialog_ids:
            return {}

        dialog_ids = list(set(dialog_ids))

        stmt = (
            select(DialogMessage)
            .where(DialogMessage.dialog_id.in_(dialog_ids))
            .distinct(DialogMessage.dialog_id)
            .order_by(DialogMessage.dialog_id, DialogMessage.created_at.desc(), DialogMessage.id.desc())
        )
        result = await session.execute(stmt)
        messages = result.scalars().all()
        return {message.dialog_id: message for message in messages}

    async def delete(self, session: AsyncSession, message_id: int) -> None:
        obj = await self.get(session, message_id)
        if obj:
            await session.delete(obj)
            await session.commit()
