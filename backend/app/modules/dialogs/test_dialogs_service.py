"""Tests for dialog locking and unlocking logic."""
from __future__ import annotations

import asyncio
from datetime import datetime
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
from app.modules.bots.models import Bot
from app.modules.channels.models import ChannelType
from app.modules.dialogs.models import Dialog, DialogMessage, DialogStatus
from app.modules.dialogs.schemas import DialogCreate
from app.modules.dialogs.service import DialogLockError, DialogsService


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


async def _create_base_entities(maker: Callable[[], AsyncSessionWrapper]):
    async with maker() as session:
        owner = User(email="owner@example.com", password_hash="x", role=UserRole.ADMIN)
        account = Account(name="Test Account", owner=owner)
        bot = Bot(name="Test Bot", description=None, account=account)
        operator = User(email="operator@example.com", password_hash="y", role=UserRole.OPERATOR)
        another_operator = User(
            email="operator2@example.com", password_hash="z", role=UserRole.OPERATOR
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
    assert unlocked.assigned_admin_id == operator.id


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
