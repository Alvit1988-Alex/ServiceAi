"""Tests for dialog locking and unlocking logic."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Callable

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.modules.accounts.models import Account, User, UserRole
from app.modules.bots.models import Bot
from app.modules.channels.models import BotChannel, ChannelType
from app.modules.channels.schemas import NormalizedIncomingMessage
from app.modules.dialogs.models import Dialog, DialogMessage, DialogStatus, MessageSender
from app.modules.dialogs.schemas import DialogCreate
from app.modules.dialogs.service import AI_FALLBACK_TEXT, DialogLockError, DialogsService


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
            BotChannel.__table__,
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
                BotChannel.__table__,
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

        channel = BotChannel(bot=bot, channel_type=ChannelType.WEBCHAT, config={"source": "test"}, is_active=True)

        session.add_all([owner, account, bot, operator, another_operator, channel])
        await session.commit()

        await session.refresh(bot)
        await session.refresh(operator)
        await session.refresh(another_operator)
        await session.refresh(channel)

        return bot, operator, another_operator, channel


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
    bot, operator, _, _channel = run(_create_base_entities(db_sessionmaker))
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
    bot, operator, another_operator, _channel = run(_create_base_entities(db_sessionmaker))
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
    bot, operator, another_operator, _channel = run(_create_base_entities(db_sessionmaker))
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
    bot, operator, _, _channel = run(_create_base_entities(db_sessionmaker))
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
    bot, operator, _, _channel = run(_create_base_entities(db_sessionmaker))
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


def test_process_incoming_message_syncs_bitrix_when_ai_fails(db_sessionmaker: Callable[[], AsyncSessionWrapper], monkeypatch):
    service = DialogsService()
    bot, _operator, _, channel = run(_create_base_entities(db_sessionmaker))

    sync_calls: list[dict] = []
    sync_called: asyncio.Event | None = None

    async def fake_sync(self, *, bot_id: int, dialog_id: int, text: str | None, dialog_created: bool) -> None:  # noqa: ANN001
        sync_calls.append({
            "bot_id": bot_id,
            "dialog_id": dialog_id,
            "text": text,
            "dialog_created": dialog_created,
        })
        if sync_called is not None:
            sync_called.set()

    monkeypatch.setattr(
        "app.modules.integrations.bitrix24.service.Bitrix24Service.sync_incoming_user_message",
        fake_sync,
    )

    class BrokenAIService:
        async def answer(self, **_kwargs):  # noqa: ANN003
            raise RuntimeError("lm studio offline")

    async def _exercise():
        nonlocal sync_called
        sync_called = asyncio.Event()

        async with db_sessionmaker() as session:
            incoming = NormalizedIncomingMessage(
                bot_id=bot.id,
                channel_id=channel.id,
                channel_type=ChannelType.WEBCHAT,
                external_chat_id="chat-ai-down",
                external_user_id="user-ai-down",
                text="help",
                payload={"source": "test"},
            )

            user_message, bot_message, _dialog, _created = await service.process_incoming_message(
                session=session,
                incoming_message=incoming,
                ai_service=BrokenAIService(),
            )
            assert sync_called is not None
            await asyncio.wait_for(sync_called.wait(), timeout=1.0)
            return user_message, bot_message

    user_message, bot_message = run(_exercise())

    assert user_message.sender == MessageSender.USER
    assert bot_message is not None
    assert bot_message.text == AI_FALLBACK_TEXT
    assert len(sync_calls) == 1
    assert sync_calls[0]["bot_id"] == bot.id
    assert sync_calls[0]["text"] == "help"
