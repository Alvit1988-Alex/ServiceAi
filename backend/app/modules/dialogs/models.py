"""Dialog and message models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class DialogStatus(str, Enum):
    AUTO = "AUTO"
    WAIT_OPERATOR = "WAIT_OPERATOR"
    WAIT_USER = "WAIT_USER"


class Dialog(Base):
    __tablename__ = "dialogs"
    __table_args__ = (Index("ix_dialog_bot_user_external", "bot_id", "user_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[DialogStatus] = mapped_column(SQLEnum(DialogStatus, name="dialog_status"), nullable=False)
    closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    bot: Mapped["Bot"] = relationship(
        "Bot",
        back_populates="dialogs",
        passive_deletes=True,
    )
    messages: Mapped[list["DialogMessage"]] = relationship(
        "DialogMessage",
        back_populates="dialog",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class MessageSender(str, Enum):
    USER = "user"
    BOT = "bot"
    OPERATOR = "operator"


class DialogMessage(Base):
    __tablename__ = "dialog_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dialog_id: Mapped[int] = mapped_column(Integer, ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=False, index=True)
    sender: Mapped[MessageSender] = mapped_column(SQLEnum(MessageSender, name="dialog_message_sender"), nullable=False)
    text: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    dialog: Mapped[Dialog] = relationship(
        "Dialog",
        back_populates="messages",
        passive_deletes=True,
    )
