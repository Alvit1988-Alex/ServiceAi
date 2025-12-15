"""Persistence models for diagnostics and integrations."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    account_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bot_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("bots.id", ondelete="SET NULL"), nullable=True)
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), default=lambda: str(uuid4()), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)

