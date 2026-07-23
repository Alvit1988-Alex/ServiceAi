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
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.modules.accounts.models import Account, User, UserRole
from app.modules.ai.schemas import AIAnswer
from app.modules.bots.models import Bot
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
                Bot.__table__,
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


def test_switch_to_auto_handoff_trigger_skips_ai(db_sessionmaker, monkeypatch):
    DummySender.sent = []
    monkeypatch.setattr("app.modules.dialogs.service.get_sender", lambda _channel: DummySender)
    service = DialogsService()
    bot, operator, _ = run(_create_base_entities(db_sessionmaker))

    class DummyWS:
        async def broadcast_to_admins(self, *_args, **_kwargs):
            return None

        async def broadcast_new_message(self, *_args, **_kwargs):
            return None

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
            dialog.assigned_admin_id = operator.id
            user_message = DialogMessage(dialog_id=dialog.id, sender=MessageSender.USER, text="оператор")
            session.add_all([dialog, user_message])
            await session.commit()
            await session.refresh(dialog)
            ai = DummyAIService(AIAnswer(can_answer=True, answer="ok", confidence=1, used_chunk_ids=[]))
            updated = await service.switch_to_auto(
                session=session,
                dialog=dialog,
                admin_id=operator.id,
                ai_service=ai,
                ws_manager=DummyWS(),
            )
            return ai.calls, updated

    calls, dialog = run(_case())
    assert calls == 0
    assert dialog.status == DialogStatus.WAIT_OPERATOR
