"""Authentication domain models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class PendingLoginStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"


class PendingLogin(Base):
    __tablename__ = "pending_logins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[PendingLoginStatus] = mapped_column(
        SQLEnum(
            PendingLoginStatus,
            name="pending_login_status",
            values_callable=lambda enum: [entry.value for entry in enum],
        ),
        nullable=False,
        default=PendingLoginStatus.PENDING.value,
    )
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OAuthLoginSessionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CONSUMED = "consumed"
    FAILED = "failed"


class OAuthLoginSession(Base):
    __tablename__ = "oauth_login_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    state_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    code_verifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[OAuthLoginSessionStatus] = mapped_column(
        SQLEnum(
            OAuthLoginSessionStatus,
            name="oauth_login_session_status",
            values_callable=lambda enum: [entry.value for entry in enum],
        ),
        nullable=False,
        default=OAuthLoginSessionStatus.PENDING.value,
    )
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completion_token: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
