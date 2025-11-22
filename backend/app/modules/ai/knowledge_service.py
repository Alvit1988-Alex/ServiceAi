"""Knowledge base service for storing files and embedding their content."""
from __future__ import annotations

from typing import Callable
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import BASE_DIR
from app.database import async_session_factory
from app.modules.ai.embeddings import EmbeddingsClient, GigaChatEmbeddingsClient
from app.modules.ai.models import KnowledgeChunk, KnowledgeFile
from app.modules.ai.storage import FileStorage


class KnowledgeService:
    def __init__(
        self,
        db_session_factory: Callable[[], AsyncSession]
        | async_sessionmaker[AsyncSession]
        | None = None,
        embeddings_client: EmbeddingsClient | None = None,
        storage: FileStorage | None = None,
        max_file_size_bytes: int = 5 * 1024 * 1024,
        total_quota_bytes: int = 50 * 1024 * 1024,
    ):
        self._session_factory = db_session_factory or async_session_factory
        self._embeddings = embeddings_client or GigaChatEmbeddingsClient()
        self._storage = storage or FileStorage(BASE_DIR / "data" / "knowledge")
        self._max_file_size_bytes = max_file_size_bytes
        self._total_quota_bytes = total_quota_bytes

    async def upload_file(self, bot_id: int, file: UploadFile) -> KnowledgeFile:
        content_bytes = await file.read()
        await self._validate_quota(bot_id=bot_id, new_file_size=len(content_bytes))

        filename = f"{uuid4().hex}_{file.filename}"
        self._storage.save(filename, content_bytes)

        text_content = self._extract_text(content_bytes)
        chunks = self._chunk_text(text_content)
        embeddings = await self._embeddings.embed_many(chunks) if chunks else []

        async with self._session() as session:
            knowledge_file = KnowledgeFile(
                bot_id=bot_id,
                file_name=filename,
                original_name=file.filename or "file",
                mime_type=file.content_type,
                size_bytes=len(content_bytes),
                chunks_count=len(chunks),
            )
            session.add(knowledge_file)
            await session.flush()

            knowledge_chunks: list[KnowledgeChunk] = []
            for idx, chunk_text in enumerate(chunks):
                embedding = embeddings[idx] if idx < len(embeddings) else []
                knowledge_chunks.append(
                    KnowledgeChunk(
                        file_id=knowledge_file.id,
                        bot_id=bot_id,
                        chunk_index=idx,
                        text=chunk_text,
                        embedding=embedding,
                    )
                )

            if knowledge_chunks:
                session.add_all(knowledge_chunks)

            await session.commit()
            await session.refresh(knowledge_file)
            return knowledge_file

    async def list_files(self, bot_id: int) -> list[KnowledgeFile]:
        async with self._session() as session:
            result = await session.execute(
                select(KnowledgeFile).where(KnowledgeFile.bot_id == bot_id)
            )
            return result.scalars().all()

    async def get_file(self, bot_id: int, file_id: int) -> KnowledgeFile | None:
        async with self._session() as session:
            result = await session.execute(
                select(KnowledgeFile).where(
                    KnowledgeFile.bot_id == bot_id, KnowledgeFile.id == file_id
                )
            )
            return result.scalars().first()

    async def delete_file(self, bot_id: int, file_id: int) -> None:
        async with self._session() as session:
            result = await session.execute(
                select(KnowledgeFile).where(
                    KnowledgeFile.bot_id == bot_id, KnowledgeFile.id == file_id
                )
            )
            knowledge_file = result.scalars().first()
            if not knowledge_file:
                return

            await session.delete(knowledge_file)
            await session.commit()

        self._storage.delete(knowledge_file.file_name)

    def _chunk_text(
        self, text: str, max_chunk_size: int = 1200, overlap: int = 200
    ) -> list[str]:
        normalized = "\n".join(line.strip() for line in text.splitlines())
        paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]

        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 2 <= max_chunk_size:
                current = f"{current}\n\n{paragraph}" if current else paragraph
            else:
                if current:
                    chunks.append(current.strip())
                remaining = paragraph
                while len(remaining) > max_chunk_size:
                    chunk = remaining[:max_chunk_size]
                    chunks.append(chunk)
                    remaining = remaining[max_chunk_size - overlap :]
                current = remaining
        if current:
            chunks.append(current.strip())

        return [chunk for chunk in chunks if chunk]

    async def _validate_quota(self, bot_id: int, new_file_size: int) -> None:
        if new_file_size > self._max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded file exceeds the allowed size",
            )

        async with self._session() as session:
            total_size = await session.scalar(
                select(func.coalesce(func.sum(KnowledgeFile.size_bytes), 0)).where(
                    KnowledgeFile.bot_id == bot_id
                )
            )
        total_size = total_size or 0

        if total_size + new_file_size > self._total_quota_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Knowledge base storage quota exceeded",
            )

    @staticmethod
    def _extract_text(content_bytes: bytes) -> str:
        return content_bytes.decode(errors="ignore")

    def _session(self) -> AsyncSession:
        return self._session_factory()


def get_knowledge_service() -> KnowledgeService:
    """Dependency injection helper for KnowledgeService."""

    return KnowledgeService()
