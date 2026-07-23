"""Bot model definitions."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modules.ai.models import AIInstructions, KnowledgeChunk, KnowledgeFile

if TYPE_CHECKING:
    from app.modules.accounts.models import Account, User
    from app.modules.channels.models import BotChannel
    from app.modules.dialogs.models import Dialog


def utcnow() -> datetime:
    return datetime.utcnow()


class BotAdminRole(str, Enum):
    superadmin = "superadmin"
    admin = "admin"


class Bot(Base):
    __tablename__ = "bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    operator_handoff_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    operator_trigger_phrases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="bots",
        passive_deletes=True,
    )
    admins: Mapped[list["BotAdmin"]] = relationship(
        "BotAdmin",
        back_populates="bot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    channels: Mapped[list["BotChannel"]] = relationship(
        "BotChannel",
        back_populates="bot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    dialogs: Mapped[list["Dialog"]] = relationship(
        "Dialog",
        back_populates="bot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    ai_instructions: Mapped[AIInstructions | None] = relationship(
        "AIInstructions",
        back_populates="bot",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    knowledge_files: Mapped[list[KnowledgeFile]] = relationship(
        "KnowledgeFile",
        back_populates="bot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    knowledge_chunks: Mapped[list[KnowledgeChunk]] = relationship(
        "KnowledgeChunk",
        back_populates="bot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class BotAdmin(Base):
    __tablename__ = "bot_admins"
    __table_args__ = (UniqueConstraint("bot_id", "user_id", name="uq_bot_admins_bot_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[BotAdminRole] = mapped_column(SQLEnum(BotAdminRole, name="bot_admin_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    bot: Mapped["Bot"] = relationship("Bot", back_populates="admins", passive_deletes=True)
    user: Mapped["User"] = relationship("User", back_populates="bot_admin_accesses", passive_deletes=True)
