"""Dialog and message models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modules.accounts.models import User
from app.modules.channels.models import ChannelType, channel_type_enum


def utcnow() -> datetime:
    return datetime.utcnow()


class DialogStatus(str, Enum):
    AUTO = "auto"
    WAIT_OPERATOR = "wait_operator"
    WAIT_USER = "wait_user"


def normalize_dialog_status(value: DialogStatus | str) -> DialogStatus:
    if isinstance(value, DialogStatus):
        return value
    if not isinstance(value, str):
        raise ValueError(f"Unknown dialog status: {value}")
    normalized = value.strip()
    try:
        return DialogStatus(normalized)
    except ValueError:
        try:
            return DialogStatus[normalized.upper()]
        except KeyError as exc:
            raise ValueError(f"Unknown dialog status: {value}") from exc


def dialog_status_enum() -> SQLEnum:
    return SQLEnum(
        DialogStatus,
        name="dialog_status",
        values_callable=lambda enum: [member.value for member in enum],
        validate_strings=True,
    )


class Dialog(Base):
    __tablename__ = "dialogs"
    __table_args__ = (
        Index("ix_dialog_bot_channel_chat", "bot_id", "channel_type", "external_chat_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_type: Mapped[ChannelType] = mapped_column(
        channel_type_enum(), nullable=False, index=True
    )
    external_chat_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[DialogStatus] = mapped_column(dialog_status_enum(), nullable=False)
    closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_user_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    unread_messages_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_admin_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    waiting_time_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    bot: Mapped["Bot"] = relationship(
        "Bot",
        back_populates="dialogs",
        passive_deletes=True,
    )
    assigned_admin: Mapped[User | None] = relationship(
        "User",
        back_populates="assigned_dialogs",
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
