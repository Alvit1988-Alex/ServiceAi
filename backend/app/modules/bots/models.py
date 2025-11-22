"""Bot model definitions."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class Bot(Base):
    __tablename__ = "bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="bots",
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
    ai_instructions: Mapped["AIInstructions" | None] = relationship(
        "AIInstructions",
        back_populates="bot",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    knowledge_files: Mapped[list["KnowledgeFile"]] = relationship(
        "KnowledgeFile",
        back_populates="bot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    knowledge_chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk",
        back_populates="bot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
