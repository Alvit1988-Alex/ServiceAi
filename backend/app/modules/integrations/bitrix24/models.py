from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class BitrixIntegration(Base):
    __tablename__ = "bitrix_integrations"
    __table_args__ = (UniqueConstraint("bot_id", name="uq_bitrix_integrations_bot_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    portal_url: Mapped[str] = mapped_column(String(255), nullable=False)
    member_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scope: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    openline_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    auto_create_lead_on_first_message: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class BitrixDialogLink(Base):
    __tablename__ = "bitrix_dialog_links"
    __table_args__ = (
        UniqueConstraint("dialog_id", name="uq_bitrix_dialog_links_dialog_id"),
        Index("ix_bitrix_dialog_links_bot_id", "bot_id"),
        Index("ix_bitrix_dialog_links_chat_id", "bitrix_chat_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dialog_id: Mapped[int] = mapped_column(Integer, ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=False)
    bot_id: Mapped[int] = mapped_column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)
    bitrix_chat_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bitrix_lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
