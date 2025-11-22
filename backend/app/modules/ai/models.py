"""AI-related models."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class AIInstructions(Base):
    __tablename__ = "ai_instructions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("bots.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    bot: Mapped["Bot"] = relationship(
        "Bot", back_populates="ai_instructions", passive_deletes=True
    )


class KnowledgeFile(Base):
    __tablename__ = "knowledge_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("bots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    chunks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    bot: Mapped["Bot"] = relationship(
        "Bot", back_populates="knowledge_files", passive_deletes=True
    )
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk",
        back_populates="file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_files.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("bots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    bot: Mapped["Bot"] = relationship(
        "Bot", back_populates="knowledge_chunks", passive_deletes=True
    )
    file: Mapped["KnowledgeFile"] = relationship(
        "KnowledgeFile", back_populates="chunks", passive_deletes=True
    )
