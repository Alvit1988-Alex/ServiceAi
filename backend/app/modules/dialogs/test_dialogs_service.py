"""Tests for dialog locking and unlocking logic."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import os
import sys

sys.path.append(str(Path(__file__).resolve().parents[3]))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
os.environ.setdefault("JWT_SECRET_KEY", "test" * 8)
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "refresh" * 5)
os.environ.setdefault("CHANNEL_CONFIG_SECRET_KEY", "secret")

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import JSONB, dialect as postgresql_dialect
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.modules.accounts.models import Account, User, UserRole, account_operators
from app.modules.ai.schemas import AIAnswer
from app.modules.bots.models import Bot, BotAdmin, BotAdminRole
from app.modules.bots.schemas import BotCreate, BotUpdate
from app.modules.channels.models import ChannelType
from app.modules.channels.schemas import NormalizedIncomingMessage
from app.modules.dialogs.models import Dialog, DialogMessage, DialogStatus, MessageSender
from app.modules.dialogs.schemas import DialogCreate
from app.modules.dialogs.service import (
    AI_CANNOT_ANSWER_TEXT,
    HANDOFF_TEXT,
    DialogLockError,
    DialogsService,
    _matches_operator_trigger,
)


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(_element, _compiler, **_kw):
    return "JSON"


class AsyncSessionWrapper:
    """Minimal async wrapper around a synchronous SQLAlchemy session."""

    def __init__(self, sync_session: Session):
        self._session = sync_session

    async def __aenter__(self) -> "AsyncSessionWrapper":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401, ANN001
        await self.close()

    def add(self, obj) -> None:  # noqa: ANN001
        self._session.add(obj)

    def add_all(self, objs) -> None:  # noqa: ANN001
        self._session.add_all(objs)

    async def execute(self, statement):  # noqa: ANN001
        return self._session.execute(statement)

    async def scalar(self, statement):  # noqa: ANN001
        return self._session.scalar(statement)

    async def get(self, entity, ident):  # noqa: ANN001
        return self._session.get(entity, ident)

    async def commit(self) -> None:
        self._session.commit()

    async def refresh(self, obj) -> None:  # noqa: ANN001
        self._session.refresh(obj)

    async def delete(self, obj) -> None:  # noqa: ANN001
        self._session.delete(obj)

    async def close(self) -> None:
        self._session.close()


@pytest.fixture()
def db_sessionmaker() -> Callable[[], AsyncSessionWrapper]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            Account.__table__,
            Bot.__table__,
            Dialog.__table__,
            DialogMessage.__table__,
        ],
    )

    sync_sessionmaker = sessionmaker(bind=engine, expire_on_commit=False)

    def factory() -> AsyncSessionWrapper:
        return AsyncSessionWrapper(sync_sessionmaker())

    try:
        yield factory
    finally:
        Base.metadata.drop_all(
            bind=engine,
            tables=[
                DialogMessage.__table__,
                Dialog.__table__,
                BotAdmin.__table__,
                Bot.__table__,
                account_operators,
                Account.__table__,
                User.__table__,
            ],
        )
        engine.dispose()


def run(coro):
    return asyncio.run(coro)


def test_dialog_status_enum_uses_lowercase_values():
    status_enum = Dialog.__table__.c.status.type
    assert status_enum.enums == ["auto", "wait_operator", "wait_user"]


async def _create_base_entities(maker: Callable[[], AsyncSessionWrapper]):
    async with maker() as session:
        owner = User(email="owner@example.com", password_hash="x", role=UserRole.admin)
        account = Account(name="Test Account", owner=owner)
        bot = Bot(name="Test Bot", description=None, account=account)
        operator = User(email="operator@example.com", password_hash="y", role=UserRole.operator)
        another_operator = User(
            email="operator2@example.com", password_hash="z", role=UserRole.operator
        )

        session.add_all([owner, account, bot, operator, another_operator])
        await session.commit()

        await session.refresh(bot)
        await session.refresh(operator)
        await session.refresh(another_operator)

        return bot, operator, another_operator


async def _create_dialog(
    service: DialogsService, maker: Callable[[], AsyncSessionWrapper], bot: Bot, chat_id: str
):
    async with maker() as session:
        dialog = await service.create(
            session=session,
            obj_in=DialogCreate(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id=chat_id,
                external_user_id=f"user-{chat_id}",
                status=DialogStatus.AUTO,
                closed=False,
            ),
        )
        return dialog


def test_lock_dialog_sets_assignment_and_flag(db_sessionmaker: Callable[[], AsyncSessionWrapper]):
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))
    dialog = run(_create_dialog(service, db_sessionmaker, bot, "lock-me"))

    async def _lock_dialog():
        async with db_sessionmaker() as session:
            return await service.lock_dialog(session=session, dialog=dialog, admin_id=operator.id)

    locked_dialog = run(_lock_dialog())
    assert locked_dialog.is_locked is True
    assert locked_dialog.assigned_admin_id == operator.id
    assert locked_dialog.locked_until is None


def test_lock_dialog_conflict_with_foreign_owner(db_sessionmaker: Callable[[], AsyncSessionWrapper]):
    service = DialogsService()
    bot, operator, another_operator = run(_create_base_entities(db_sessionmaker))
    dialog = run(_create_dialog(service, db_sessionmaker, bot, "taken"))

    async def _prepare_and_lock_with_other():
        async with db_sessionmaker() as session:
            dialog.assigned_admin_id = operator.id
            dialog.updated_at = datetime.utcnow()
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)

            with pytest.raises(DialogLockError):
                await service.lock_dialog(session=session, dialog=dialog, admin_id=another_operator.id)

    run(_prepare_and_lock_with_other())


def test_unlock_dialog_requires_owner(db_sessionmaker: Callable[[], AsyncSessionWrapper]):
    service = DialogsService()
    bot, operator, another_operator = run(_create_base_entities(db_sessionmaker))
    dialog = run(_create_dialog(service, db_sessionmaker, bot, "unlockable"))

    async def _unlock_flow():
        async with db_sessionmaker() as session:
            dialog_locked = await service.lock_dialog(session=session, dialog=dialog, admin_id=operator.id)

            with pytest.raises(DialogLockError):
                await service.unlock_dialog(session=session, dialog=dialog_locked, admin_id=another_operator.id)

            return await service.unlock_dialog(session=session, dialog=dialog_locked, admin_id=operator.id)

    unlocked = run(_unlock_flow())
    assert unlocked.is_locked is False
    assert unlocked.assigned_admin_id is None


def test_list_filters_by_lock_state(db_sessionmaker: Callable[[], AsyncSessionWrapper]):
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))
    locked_dialog = run(_create_dialog(service, db_sessionmaker, bot, "locked"))
    unlocked_dialog = run(_create_dialog(service, db_sessionmaker, bot, "unlocked"))

    async def _lock_and_list():
        async with db_sessionmaker() as session:
            await service.lock_dialog(session=session, dialog=locked_dialog, admin_id=operator.id)

            locked_items, total_locked, _ = await service.list(
                session=session, filters={"bot_id": bot.id, "is_locked": True}
            )
            unlocked_items, total_unlocked, _ = await service.list(
                session=session, filters={"bot_id": bot.id, "is_locked": False}
            )
            return locked_items, total_locked, unlocked_items, total_unlocked

    locked_items, total_locked, unlocked_items, total_unlocked = run(_lock_and_list())
    assert {d.id for d in locked_items} == {locked_dialog.id}
    assert total_locked == 1
    assert {d.id for d in unlocked_items} == {unlocked_dialog.id}
    assert total_unlocked == 1


def test_unlock_if_expired(db_sessionmaker: Callable[[], AsyncSessionWrapper]):
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))
    dialog = run(_create_dialog(service, db_sessionmaker, bot, "expire"))

    async def _lock_and_expire_dialog():
        async with db_sessionmaker() as session:
            locked_dialog = await service.lock_dialog(session=session, dialog=dialog, admin_id=operator.id)
            locked_dialog.locked_until = datetime.utcnow() - timedelta(seconds=1)
            session.add(locked_dialog)
            await session.commit()
            await session.refresh(locked_dialog)
            return locked_dialog

    run(_lock_and_expire_dialog())

    async def _unlock_expired_dialog():
        async with db_sessionmaker() as session:
            fetched_dialog = await service.get(session=session, bot_id=bot.id, dialog_id=dialog.id)
            unlocked_dialog, unlocked = await service.unlock_if_expired(session=session, dialog=fetched_dialog)
            return unlocked_dialog, unlocked

    unlocked_dialog, unlocked = run(_unlock_expired_dialog())

    assert unlocked is True
    assert unlocked_dialog.is_locked is False
    assert unlocked_dialog.assigned_admin_id is None
    assert unlocked_dialog.locked_until is None



class DummyAIService:
    def __init__(self, answer=None, exc: Exception | None = None):
        self.answer_value = answer
        self.exc = exc
        self.calls = 0

    async def answer(self, **_kwargs):
        self.calls += 1
        if self.exc:
            raise self.exc
        return self.answer_value


class DummySender:
    sent: list[tuple[int, str, str]] = []

    async def send_text(self, *, bot_id: int, external_chat_id: str, text: str):
        self.sent.append((bot_id, external_chat_id, text))


def _incoming(bot_id: int, text: str) -> NormalizedIncomingMessage:
    return NormalizedIncomingMessage(
        bot_id=bot_id,
        channel_id=1,
        channel_type=ChannelType.WEBCHAT,
        external_chat_id="chat-1",
        external_user_id="user-1",
        text=text,
    )


def test_bot_operator_handoff_defaults():
    bot = Bot(name="Bot", description=None, account_id=1)
    assert bot.operator_handoff_enabled is None or bot.operator_handoff_enabled is False
    assert bot.operator_trigger_phrases is None or bot.operator_trigger_phrases == []
    created = BotCreate(name="Bot")
    assert created.operator_handoff_enabled is False
    assert created.operator_trigger_phrases == []


def test_bot_operator_trigger_phrase_validation():
    created = BotCreate(
        name="Bot",
        operator_handoff_enabled=True,
        operator_trigger_phrases=[" оператор ", "", "Оператор", "менеджер"],
    )
    assert created.operator_trigger_phrases == ["оператор", "менеджер"]

    updated = BotUpdate(operator_handoff_enabled=True, operator_trigger_phrases=[" A ", "a", "B"])
    assert updated.operator_trigger_phrases == ["A", "B"]

    with pytest.raises(ValueError):
        BotCreate(name="Bot", operator_trigger_phrases=["x"] * 101)
    with pytest.raises(ValueError):
        BotUpdate(operator_trigger_phrases=["x" * 201])
    with pytest.raises(ValueError):
        BotUpdate(operator_handoff_enabled=None)


def test_operator_trigger_matching_normalizes_text():
    assert _matches_operator_trigger("ПОЗОВИТЕ, пожалуйста, оператора!", ["позовите пожалуйста оператора"])
    assert _matches_operator_trigger("хочу\n\t менеджера", ["хочу менеджера"])
    assert not _matches_operator_trigger("хочу менеджера", ["позовите оператора"])


def test_process_incoming_handoff_trigger_skips_ai(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, _, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            db_bot = await session.get(Bot, bot.id)
            db_bot.operator_handoff_enabled = True
            db_bot.operator_trigger_phrases = ["позовите пожалуйста оператора"]
            await session.commit()
            ai = DummyAIService(AIAnswer(can_answer=True, answer="ok", confidence=1, used_chunk_ids=[]))
            _user, system, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "ПОЗОВИТЕ, пожалуйста, оператора!"),
                ai_service=ai,
            )
            return ai.calls, system, dialog

    calls, system, dialog = run(_case())
    assert calls == 0
    assert dialog.status == DialogStatus.WAIT_OPERATOR
    assert system.text == HANDOFF_TEXT
    assert DummySender.sent == [(bot.id, "chat-1", HANDOFF_TEXT)]


def test_process_incoming_handoff_off_trigger_uses_ai(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, _, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            db_bot = await session.get(Bot, bot.id)
            db_bot.operator_handoff_enabled = False
            db_bot.operator_trigger_phrases = ["оператор"]
            await session.commit()
            ai = DummyAIService(AIAnswer(can_answer=True, answer="Ответ", confidence=1, used_chunk_ids=[]))
            _user, bot_message, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "оператор"),
                ai_service=ai,
            )
            return ai.calls, bot_message, dialog

    calls, bot_message, dialog = run(_case())
    assert calls == 1
    assert dialog.status == DialogStatus.WAIT_USER
    assert bot_message.text == "Ответ"


def test_process_incoming_preserves_auto_status_after_ai_answer(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            dialog, _ = await service.get_or_create_dialog(
                session=session,
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
            )
            dialog.status = DialogStatus.WAIT_OPERATOR
            dialog.assigned_admin_id = operator.id
            dialog.is_locked = True
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)

            await service.switch_to_auto(session=session, dialog=dialog, admin_id=operator.id)
            ai = DummyAIService(AIAnswer(can_answer=True, answer="Автоответ", confidence=1, used_chunk_ids=[]))
            _user, bot_message, updated_dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "новый вопрос"),
                ai_service=ai,
            )
            return ai.calls, bot_message, updated_dialog

    calls, bot_message, dialog = run(_case())
    assert calls == 1
    assert bot_message.text == "Автоответ"
    assert dialog.status == DialogStatus.AUTO
    assert dialog.assigned_admin_id is None
    assert dialog.is_locked is False
    assert DummySender.sent == [(bot.id, "chat-1", "Автоответ")]


@pytest.mark.parametrize(
    ("enabled", "ai", "expected_status", "expected_text"),
    [
        (True, DummyAIService(AIAnswer(can_answer=False, answer=None, confidence=0, used_chunk_ids=[])), DialogStatus.WAIT_OPERATOR, HANDOFF_TEXT),
        (True, DummyAIService(exc=RuntimeError("ai unavailable")), DialogStatus.WAIT_OPERATOR, HANDOFF_TEXT),
        (False, DummyAIService(AIAnswer(can_answer=False, answer=None, confidence=0, used_chunk_ids=[])), DialogStatus.WAIT_USER, AI_CANNOT_ANSWER_TEXT),
        (False, DummyAIService(exc=RuntimeError("ai unavailable")), DialogStatus.WAIT_USER, AI_CANNOT_ANSWER_TEXT),
    ],
)
def test_process_incoming_ai_fallback_respects_handoff(enabled, ai, expected_status, expected_text, db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, _, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            db_bot = await session.get(Bot, bot.id)
            db_bot.operator_handoff_enabled = enabled
            await session.commit()
            _user, message, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "вопрос"),
                ai_service=ai,
            )
            return message, dialog

    message, dialog = run(_case())
    assert dialog.status == expected_status
    assert message.text == expected_text
    assert DummySender.sent == [(bot.id, "chat-1", expected_text)]


def test_process_incoming_locked_operator_priority_skips_ai(db_sessionmaker):
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            dialog, _ = await service.get_or_create_dialog(
                session=session,
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
            )
            dialog.assigned_admin_id = operator.id
            dialog.is_locked = True
            dialog.locked_until = datetime.utcnow() + timedelta(minutes=5)
            session.add(dialog)
            await session.commit()
            ai = DummyAIService(AIAnswer(can_answer=True, answer="ok", confidence=1, used_chunk_ids=[]))
            _user, system, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "оператор"),
                ai_service=ai,
            )
            return ai.calls, system, dialog

    calls, system, dialog = run(_case())
    assert calls == 0
    assert system is None
    assert dialog.assigned_admin_id == operator.id


def test_switch_to_auto_does_not_reprocess_last_trigger_message(db_sessionmaker):
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            db_bot = await session.get(Bot, bot.id)
            db_bot.operator_handoff_enabled = True
            db_bot.operator_trigger_phrases = ["оператор"]
            await session.commit()
            dialog, _ = await service.get_or_create_dialog(
                session=session,
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
            )
            dialog.status = DialogStatus.WAIT_OPERATOR
            dialog.assigned_admin_id = operator.id
            dialog.is_locked = True
            user_message = DialogMessage(dialog_id=dialog.id, sender=MessageSender.USER, text="оператор")
            session.add_all([dialog, user_message])
            await session.commit()
            await session.refresh(dialog)

            before_count = (await session.execute(select(DialogMessage).where(DialogMessage.dialog_id == dialog.id))).scalars().all()
            updated = await service.switch_to_auto(session=session, dialog=dialog, admin_id=operator.id)
            after_count = (await session.execute(select(DialogMessage).where(DialogMessage.dialog_id == dialog.id))).scalars().all()
            return updated, len(before_count), len(after_count), dialog.id

    dialog, before_count, after_count, original_id = run(_case())
    assert dialog.id == original_id
    assert before_count == 1
    assert after_count == 1
    assert dialog.status == DialogStatus.AUTO
    assert dialog.closed is False
    assert dialog.assigned_admin_id is None
    assert dialog.is_locked is False
    assert dialog.locked_until is None




def test_get_or_create_dialog_locks_bot_before_open_dialog_lookup(db_sessionmaker):
    service = DialogsService()
    bot, _, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            scalar_statements = []
            original_scalar = session.scalar

            async def scalar_spy(statement):
                scalar_statements.append(statement)
                return await original_scalar(statement)

            session.scalar = scalar_spy
            dialog, created = await service.get_or_create_dialog(
                session=session,
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="get-or-create-lock",
                external_user_id="get-or-create-lock-user",
            )
            return dialog, created, scalar_statements

    dialog, created, scalar_statements = run(_case())
    assert dialog.bot_id == bot.id
    assert created is True
    assert len(scalar_statements) == 1

    bot_lock_statement = scalar_statements[0]
    compiled = str(bot_lock_statement.compile(dialect=postgresql_dialect()))
    assert "FROM bots" in compiled
    assert "WHERE bots.id" in compiled
    assert "FOR UPDATE" in compiled

def test_switch_to_auto_closed_dialog_locks_bot_before_duplicate_check(db_sessionmaker):
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            dialog = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="lock-structural",
                external_user_id="lock-structural-user",
                status=DialogStatus.WAIT_OPERATOR,
                closed=True,
                assigned_admin_id=operator.id,
                is_locked=True,
            )
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)

            scalar_statements = []
            original_scalar = session.scalar

            async def scalar_spy(statement):
                scalar_statements.append(statement)
                return await original_scalar(statement)

            session.scalar = scalar_spy
            updated = await service.switch_to_auto(session=session, dialog=dialog, admin_id=operator.id)
            return updated, scalar_statements

    dialog, scalar_statements = run(_case())
    assert dialog.status == DialogStatus.AUTO
    assert dialog.closed is False
    assert len(scalar_statements) >= 2

    bot_lock_statement = scalar_statements[0]
    compiled = str(bot_lock_statement.compile(dialect=postgresql_dialect()))
    assert "FROM bots" in compiled
    assert "WHERE bots.id" in compiled
    assert "FOR UPDATE" in compiled


def test_switch_to_auto_open_dialog_does_not_lock_bot(db_sessionmaker):
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            dialog, _ = await service.get_or_create_dialog(
                session=session,
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="open-no-lock",
                external_user_id="open-no-lock-user",
            )
            dialog.status = DialogStatus.WAIT_OPERATOR
            dialog.assigned_admin_id = operator.id
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)

            scalar_statements = []
            original_scalar = session.scalar

            async def scalar_spy(statement):
                scalar_statements.append(statement)
                return await original_scalar(statement)

            session.scalar = scalar_spy
            updated = await service.switch_to_auto(session=session, dialog=dialog, admin_id=operator.id)
            return updated, scalar_statements

    dialog, scalar_statements = run(_case())
    assert dialog.status == DialogStatus.AUTO
    assert dialog.closed is False
    assert scalar_statements == []

def test_switch_to_auto_reopens_closed_dialog(db_sessionmaker):
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            dialog = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="legacy",
                external_user_id="legacy-user",
                status=DialogStatus.WAIT_OPERATOR,
                closed=True,
                assigned_admin_id=operator.id,
                is_locked=True,
                locked_until=datetime.utcnow() + timedelta(minutes=5),
            )
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)
            original_id = dialog.id

            updated = await service.switch_to_auto(session=session, dialog=dialog, admin_id=operator.id)
            return updated, original_id

    dialog, original_id = run(_case())
    assert dialog.id == original_id
    assert dialog.closed is False
    assert dialog.status == DialogStatus.AUTO
    assert dialog.assigned_admin_id is None
    assert dialog.is_locked is False
    assert dialog.locked_until is None


def test_switch_to_auto_rejects_reopen_when_another_active_dialog_exists(db_sessionmaker):
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            legacy = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="duplicate",
                external_user_id="legacy-user",
                status=DialogStatus.WAIT_OPERATOR,
                closed=True,
                assigned_admin_id=operator.id,
                is_locked=True,
            )
            active = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="duplicate",
                external_user_id="active-user",
                status=DialogStatus.WAIT_USER,
                closed=False,
            )
            session.add_all([legacy, active])
            await session.commit()
            await session.refresh(legacy)
            await session.refresh(active)

            with pytest.raises(DialogLockError, match="активный диалог"):
                await service.switch_to_auto(session=session, dialog=legacy, admin_id=operator.id)

            await session.refresh(legacy)
            await session.refresh(active)
            return legacy, active

    legacy, active = run(_case())
    assert legacy.closed is True
    assert legacy.status == DialogStatus.WAIT_OPERATOR
    assert legacy.assigned_admin_id == operator.id
    assert legacy.is_locked is True
    assert legacy.locked_until is None
    assert active.closed is False
    assert active.status == DialogStatus.WAIT_USER
    assert active.assigned_admin_id is None
    assert active.is_locked is False


def test_get_or_create_reuses_dialog_after_switch_to_auto(db_sessionmaker):
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            dialog, _ = await service.get_or_create_dialog(
                session=session,
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
            )
            dialog.status = DialogStatus.WAIT_OPERATOR
            dialog.assigned_admin_id = operator.id
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)

            updated = await service.switch_to_auto(session=session, dialog=dialog, admin_id=operator.id)
            fetched, created = await service.get_or_create_dialog(
                session=session,
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
            )
            return updated.id, fetched.id, created

    updated_id, fetched_id, created = run(_case())
    assert fetched_id == updated_id
    assert created is False

def test_count_waiting_operator_dialogs_filters_status_closed_and_access(db_sessionmaker):
    service = DialogsService()

    async def _case():
        async with db_sessionmaker() as session:
            owner = User(email="count-owner@example.com", password_hash="x", role=UserRole.owner)
            other_owner = User(email="count-other@example.com", password_hash="x", role=UserRole.owner)
            operator = User(email="count-operator@example.com", password_hash="x", role=UserRole.operator)
            owner_account = Account(name="Owner Account", public_id="11111111", owner=owner)
            other_account = Account(name="Other Account", public_id="22222222", owner=other_owner)
            owned_bot = Bot(name="Owned", description=None, account=owner_account)
            delegated_bot = Bot(name="Delegated", description=None, account=other_account)
            foreign_bot = Bot(name="Foreign", description=None, account=other_account)
            session.add_all([owner, other_owner, operator, owner_account, other_account, owned_bot, delegated_bot, foreign_bot])
            await session.commit()
            await session.refresh(owner)
            await session.refresh(operator)
            await session.refresh(owned_bot)
            await session.refresh(delegated_bot)
            await session.refresh(foreign_bot)

            session.add(BotAdmin(bot_id=delegated_bot.id, user_id=operator.id, role=BotAdminRole.admin))
            session.add_all([
                Dialog(bot_id=owned_bot.id, channel_type=ChannelType.WEBCHAT, external_chat_id="a", external_user_id="a", status=DialogStatus.WAIT_OPERATOR, closed=False),
                Dialog(bot_id=owned_bot.id, channel_type=ChannelType.WEBCHAT, external_chat_id="b", external_user_id="b", status=DialogStatus.AUTO, closed=False),
                Dialog(bot_id=owned_bot.id, channel_type=ChannelType.WEBCHAT, external_chat_id="c", external_user_id="c", status=DialogStatus.WAIT_USER, closed=False),
                Dialog(bot_id=owned_bot.id, channel_type=ChannelType.WEBCHAT, external_chat_id="d", external_user_id="d", status=DialogStatus.WAIT_OPERATOR, closed=True),
                Dialog(bot_id=owned_bot.id, channel_type=ChannelType.WEBCHAT, external_chat_id="assigned", external_user_id="assigned", status=DialogStatus.WAIT_OPERATOR, closed=False, assigned_admin_id=operator.id),
                Dialog(bot_id=delegated_bot.id, channel_type=ChannelType.WEBCHAT, external_chat_id="e", external_user_id="e", status=DialogStatus.WAIT_OPERATOR, closed=False),
                Dialog(bot_id=foreign_bot.id, channel_type=ChannelType.WEBCHAT, external_chat_id="f", external_user_id="f", status=DialogStatus.WAIT_OPERATOR, closed=False),
            ])
            await session.commit()

            owner_count = await service.count_waiting_operator_dialogs(session=session, current_user=owner)
            operator_count = await service.count_waiting_operator_dialogs(session=session, current_user=operator)
            admin = User(email="count-admin@example.com", password_hash="x", role=UserRole.admin)
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            admin_count = await service.count_waiting_operator_dialogs(session=session, current_user=admin)
            return owner_count, operator_count, admin_count

    owner_count, operator_count, admin_count = run(_case())
    assert owner_count == 1
    assert operator_count == 1
    assert admin_count == 3


def test_count_waiting_operator_dialogs_excludes_assigned_dialogs(db_sessionmaker):
    service = DialogsService()

    async def _case():
        async with db_sessionmaker() as session:
            owner = User(email="assigned-owner@example.com", password_hash="x", role=UserRole.owner)
            operator = User(email="assigned-operator@example.com", password_hash="x", role=UserRole.operator)
            account = Account(name="Assigned Account", public_id="44444444", owner=owner)
            bot = Bot(name="Assigned Bot", description=None, account=account)
            session.add_all([owner, operator, account, bot])
            await session.commit()
            await session.refresh(owner)
            await session.refresh(operator)
            await session.refresh(bot)

            session.add_all([
                Dialog(
                    bot_id=bot.id,
                    channel_type=ChannelType.WEBCHAT,
                    external_chat_id="unassigned",
                    external_user_id="unassigned",
                    status=DialogStatus.WAIT_OPERATOR,
                    closed=False,
                    assigned_admin_id=None,
                ),
                Dialog(
                    bot_id=bot.id,
                    channel_type=ChannelType.WEBCHAT,
                    external_chat_id="assigned",
                    external_user_id="assigned",
                    status=DialogStatus.WAIT_OPERATOR,
                    closed=False,
                    assigned_admin_id=operator.id,
                ),
            ])
            await session.commit()

            return await service.count_waiting_operator_dialogs(session=session, current_user=owner)

    assert run(_case()) == 1


def test_count_waiting_operator_dialogs_returns_zero(db_sessionmaker):
    service = DialogsService()

    async def _case():
        async with db_sessionmaker() as session:
            user = User(email="zero@example.com", password_hash="x", role=UserRole.owner)
            account = Account(name="Zero", public_id="33333333", owner=user)
            bot = Bot(name="Zero Bot", description=None, account=account)
            session.add_all([user, account, bot])
            await session.commit()
            await session.refresh(user)
            return await service.count_waiting_operator_dialogs(session=session, current_user=user)

    assert run(_case()) == 0


def test_handoff_sets_operator_mode_and_blocks_ai_before_timeout(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, _, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            db_bot = await session.get(Bot, bot.id)
            db_bot.operator_handoff_enabled = True
            db_bot.operator_trigger_phrases = ["оператор"]
            await session.commit()
            ai = DummyAIService(AIAnswer(can_answer=True, answer="first", confidence=1, used_chunk_ids=[]))
            _user, _system, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "оператор"),
                ai_service=ai,
            )
            started_at = dialog.operator_mode_started_at
            ai.calls = 0
            _user2, bot_message, dialog, _created2 = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "следующий вопрос"),
                ai_service=ai,
            )
            messages = (await session.execute(select(DialogMessage).where(DialogMessage.dialog_id == dialog.id))).scalars().all()
            return ai.calls, bot_message, dialog, started_at, messages

    calls, bot_message, dialog, started_at, messages = run(_case())
    assert started_at is not None
    assert calls == 0
    assert bot_message is None
    assert dialog.status == DialogStatus.WAIT_OPERATOR
    assert dialog.operator_mode_started_at == started_at
    assert dialog.unread_messages_count == 2
    assert [message.sender for message in messages].count(MessageSender.BOT) == 1


def test_legacy_wait_operator_without_operator_mode_date_starts_timer_and_skips_ai(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            dialog = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
                status=DialogStatus.WAIT_OPERATOR,
                closed=False,
                assigned_admin_id=operator.id,
                is_locked=True,
                operator_mode_started_at=None,
                unread_messages_count=1,
            )
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)
            ai = DummyAIService(AIAnswer(can_answer=True, answer="ai", confidence=1, used_chunk_ids=[]))
            user_message, bot_message, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "legacy message"),
                ai_service=ai,
            )
            started_at = dialog.operator_mode_started_at
            first_unread = dialog.unread_messages_count
            first_assigned_admin_id = dialog.assigned_admin_id
            ai.calls = 0
            _user2, second_bot_message, dialog, _created2 = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "legacy second message"),
                ai_service=ai,
            )
            messages = (await session.execute(select(DialogMessage).where(DialogMessage.dialog_id == dialog.id))).scalars().all()
            return (
                user_message,
                bot_message,
                started_at,
                first_unread,
                first_assigned_admin_id,
                ai.calls,
                second_bot_message,
                dialog,
                messages,
            )

    (
        user_message,
        bot_message,
        started_at,
        first_unread,
        first_assigned_admin_id,
        second_calls,
        second_bot_message,
        dialog,
        messages,
    ) = run(_case())
    assert user_message.sender == MessageSender.USER
    assert bot_message is None
    assert started_at is not None
    assert first_unread == 2
    assert first_assigned_admin_id == operator.id
    assert second_calls == 0
    assert second_bot_message is None
    assert dialog.status == DialogStatus.WAIT_OPERATOR
    assert dialog.assigned_admin_id == operator.id
    assert dialog.operator_mode_started_at == started_at
    assert dialog.unread_messages_count == 3
    assert [message.sender for message in messages] == [MessageSender.USER, MessageSender.USER]


def test_handoff_without_operator_answer_allows_ai_after_timeout_but_remains_waiting(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            dialog = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
                status=DialogStatus.WAIT_OPERATOR,
                closed=False,
                assigned_admin_id=operator.id,
                is_locked=True,
                operator_mode_started_at=datetime.utcnow() - timedelta(hours=1, minutes=1),
                unread_messages_count=3,
            )
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)
            ai = DummyAIService(AIAnswer(can_answer=True, answer="timeout answer", confidence=1, used_chunk_ids=[]))
            _user, bot_message, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "после часа"),
                ai_service=ai,
            )
            owner = await session.get(User, bot.account.owner_id)
            count = await service.count_waiting_operator_dialogs(session=session, current_user=owner)
            return ai.calls, bot_message, dialog, count

    calls, bot_message, dialog, count = run(_case())
    assert calls == 1
    assert bot_message.text == "timeout answer"
    assert dialog.status == DialogStatus.WAIT_OPERATOR
    assert dialog.assigned_admin_id is None
    assert dialog.is_locked is False
    assert dialog.unread_messages_count == 4
    assert count == 1
    assert DummySender.sent == [(bot.id, "chat-1", "timeout answer")]


def test_wait_user_ai_fallback_handoff_starts_operator_mode_and_blocks_next_message(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, _, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            db_bot = await session.get(Bot, bot.id)
            db_bot.operator_handoff_enabled = True
            dialog = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
                status=DialogStatus.WAIT_USER,
                closed=False,
                operator_mode_started_at=None,
            )
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)
            ai = DummyAIService(AIAnswer(can_answer=False, answer=None, confidence=0, used_chunk_ids=[]))
            user_message, handoff_message, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "fallback question"),
                ai_service=ai,
            )
            first_calls = ai.calls
            started_at = dialog.operator_mode_started_at
            first_unread = dialog.unread_messages_count
            ai.calls = 0
            second_user_message, second_bot_message, dialog, _created2 = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "next question"),
                ai_service=ai,
            )
            messages = (await session.execute(select(DialogMessage).where(DialogMessage.dialog_id == dialog.id))).scalars().all()
            return (
                user_message,
                handoff_message,
                first_calls,
                started_at,
                first_unread,
                second_user_message,
                second_bot_message,
                ai.calls,
                dialog,
                messages,
            )

    (
        user_message,
        handoff_message,
        first_calls,
        started_at,
        first_unread,
        second_user_message,
        second_bot_message,
        second_calls,
        dialog,
        messages,
    ) = run(_case())
    assert user_message.sender == MessageSender.USER
    assert handoff_message.text == HANDOFF_TEXT
    assert first_calls == 1
    assert started_at is not None
    assert first_unread == 1
    assert second_user_message.sender == MessageSender.USER
    assert second_bot_message is None
    assert second_calls == 0
    assert dialog.status == DialogStatus.WAIT_OPERATOR
    assert dialog.operator_mode_started_at == started_at
    assert dialog.unread_messages_count == 2
    assert [message.sender for message in messages] == [MessageSender.USER, MessageSender.BOT, MessageSender.USER]
    assert DummySender.sent == [(bot.id, "chat-1", HANDOFF_TEXT)]


def test_wait_user_trigger_handoff_starts_operator_mode_without_ai(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, _, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            db_bot = await session.get(Bot, bot.id)
            db_bot.operator_handoff_enabled = True
            db_bot.operator_trigger_phrases = ["оператор"]
            dialog = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
                status=DialogStatus.WAIT_USER,
                closed=False,
                operator_mode_started_at=None,
            )
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)
            ai = DummyAIService(AIAnswer(can_answer=True, answer="ai", confidence=1, used_chunk_ids=[]))
            user_message, handoff_message, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "позовите оператора"),
                ai_service=ai,
            )
            return user_message, handoff_message, ai.calls, dialog

    user_message, handoff_message, calls, dialog = run(_case())
    assert user_message.sender == MessageSender.USER
    assert calls == 0
    assert handoff_message.text == HANDOFF_TEXT
    assert dialog.status == DialogStatus.WAIT_OPERATOR
    assert dialog.operator_mode_started_at is not None
    assert dialog.unread_messages_count == 1
    assert DummySender.sent == [(bot.id, "chat-1", HANDOFF_TEXT)]


def test_operator_message_restarts_operator_mode_and_blocks_ai(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            dialog = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
                status=DialogStatus.WAIT_OPERATOR,
                closed=False,
                assigned_admin_id=operator.id,
                is_locked=True,
                operator_mode_started_at=datetime.utcnow() - timedelta(hours=2),
            )
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)
            _msg, dialog, _ = await service.add_message(
                session=session,
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
                sender=MessageSender.OPERATOR,
                text="ответ оператора",
                operator_admin_id=operator.id,
            )
            first_reply_at = dialog.operator_mode_started_at
            _msg, dialog, _ = await service.add_message(
                session=session,
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
                sender=MessageSender.OPERATOR,
                text="второй ответ",
                operator_admin_id=operator.id,
            )
            second_reply_at = dialog.operator_mode_started_at
            ai = DummyAIService(AIAnswer(can_answer=True, answer="ai", confidence=1, used_chunk_ids=[]))
            _user, bot_message, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "вопрос"),
                ai_service=ai,
            )
            return ai.calls, bot_message, dialog, first_reply_at, second_reply_at

    calls, bot_message, dialog, first_reply_at, second_reply_at = run(_case())
    assert first_reply_at is not None
    assert second_reply_at is not None
    assert second_reply_at >= first_reply_at
    assert calls == 0
    assert bot_message is None
    assert dialog.status == DialogStatus.WAIT_OPERATOR
    assert dialog.assigned_admin_id == operator.id


def test_user_messages_do_not_extend_operator_mode(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, _, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            started_at = datetime.utcnow() - timedelta(minutes=30)
            dialog = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
                status=DialogStatus.WAIT_OPERATOR,
                closed=False,
                operator_mode_started_at=started_at,
            )
            session.add(dialog)
            await session.commit()
            ai = DummyAIService(AIAnswer(can_answer=True, answer="ai", confidence=1, used_chunk_ids=[]))
            await service.process_incoming_message(session=session, incoming_message=_incoming(bot.id, "раз"), ai_service=ai)
            await service.process_incoming_message(session=session, incoming_message=_incoming(bot.id, "два"), ai_service=ai)
            dialog = await session.get(Dialog, dialog.id)
            before_expiry = dialog.operator_mode_started_at
            dialog.operator_mode_started_at = datetime.utcnow() - timedelta(hours=1, minutes=1)
            await session.commit()
            ai.calls = 0
            _user, bot_message, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "три"),
                ai_service=ai,
            )
            return before_expiry, started_at, ai.calls, bot_message, dialog

    before_expiry, started_at, calls, bot_message, dialog = run(_case())
    assert before_expiry == started_at
    assert calls == 1
    assert bot_message.text == "ai"
    assert dialog.status == DialogStatus.WAIT_OPERATOR


def test_switch_to_auto_clears_operator_mode_and_allows_ai_immediately(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            dialog = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
                status=DialogStatus.WAIT_OPERATOR,
                closed=False,
                assigned_admin_id=operator.id,
                is_locked=True,
                operator_mode_started_at=datetime.utcnow(),
            )
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)
            await service.switch_to_auto(session=session, dialog=dialog, admin_id=operator.id)
            ai = DummyAIService(AIAnswer(can_answer=True, answer="auto", confidence=1, used_chunk_ids=[]))
            _user, bot_message, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "сразу"),
                ai_service=ai,
            )
            return ai.calls, bot_message, dialog

    calls, bot_message, dialog = run(_case())
    assert calls == 1
    assert bot_message.text == "auto"
    assert dialog.status == DialogStatus.AUTO
    assert dialog.operator_mode_started_at is None
    assert dialog.assigned_admin_id is None
    assert dialog.is_locked is False


def test_ai_failure_after_operator_timeout_keeps_waiting_and_unread(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    async def _case():
        async with db_sessionmaker() as session:
            db_bot = await session.get(Bot, bot.id)
            db_bot.operator_handoff_enabled = True
            dialog = Dialog(
                bot_id=bot.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-1",
                external_user_id="user-1",
                status=DialogStatus.WAIT_OPERATOR,
                closed=False,
                assigned_admin_id=operator.id,
                is_locked=True,
                operator_mode_started_at=datetime.utcnow() - timedelta(hours=2),
                unread_messages_count=5,
            )
            session.add(dialog)
            await session.commit()
            ai = DummyAIService(AIAnswer(can_answer=False, answer=None, confidence=0, used_chunk_ids=[]))
            _user, message, dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=_incoming(bot.id, "не знаю"),
                ai_service=ai,
            )
            return ai.calls, message, dialog

    calls, message, dialog = run(_case())
    assert calls == 1
    assert message.text == HANDOFF_TEXT
    assert dialog.status == DialogStatus.WAIT_OPERATOR
    assert dialog.assigned_admin_id is None
    assert dialog.unread_messages_count == 6
