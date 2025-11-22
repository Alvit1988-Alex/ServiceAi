"""Channel persistence model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP_GREEN = "whatsapp_green"
    WHATSAPP_360 = "whatsapp_360"
    WHATSAPP_CUSTOM = "whatsapp_custom"
    AVITO = "avito"
    MAX = "max"
    WEBCHAT = "webchat"


class BotChannel(Base):
    __tablename__ = "bot_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_type: Mapped[ChannelType] = mapped_column(SQLEnum(ChannelType, name="channel_type"), nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    bot: Mapped["Bot"] = relationship(
        "Bot",
        back_populates="channels",
        passive_deletes=True,
    )
