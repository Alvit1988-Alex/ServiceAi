"""Knowledge base service for storing files and embedding their content."""
from __future__ import annotations

import mimetypes
import os
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
        max_file_size_bytes: int = 2 * 1024 * 1024,
        total_quota_bytes: int = 10 * 1024 * 1024,
    ):
        self._session_factory = db_session_factory or async_session_factory
        self._embeddings = embeddings_client or GigaChatEmbeddingsClient()
        self._storage = storage or FileStorage(BASE_DIR / "data" / "knowledge")
        self._max_file_size_bytes = max_file_size_bytes
        self._total_quota_bytes = total_quota_bytes

    async def upload_file(self, bot_id: int, file: UploadFile) -> KnowledgeFile:
        content_bytes = await file.read()
        await self._validate_quota(bot_id=bot_id, new_file_size=len(content_bytes))

        filename = f"{uuid4().hex}_{os.path.basename(file.filename or 'file')}"
        file_path = self._storage.save(bot_id, filename, content_bytes)
        mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""

        text_content = self._extract_text(str(file_path), mime_type)
        chunks = self._split_to_chunks(text_content)

        embeddings: list[tuple[str, list[float]]] = []
        for chunk in chunks:
            if chunk.strip():
                embedding = await self._embeddings.embed_text(chunk)
                if not embedding:
                    continue
                embeddings.append((chunk, embedding))

        async with self._session() as session:
            knowledge_file = KnowledgeFile(
                bot_id=bot_id,
                file_name=os.path.basename(str(file_path)),
                original_name=file.filename or "file",
                mime_type=mime_type,
                size_bytes=len(content_bytes),
                chunks_count=len(embeddings),
            )
            session.add(knowledge_file)
            await session.flush()

            for idx, (chunk_text, embedding) in enumerate(embeddings):
                session.add(
                    KnowledgeChunk(
                        file_id=knowledge_file.id,
                        bot_id=bot_id,
                        chunk_index=idx,
                        text=chunk_text,
                        embedding=embedding,
                    )
                )

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

        self._storage.delete(bot_id, knowledge_file.file_name)

    @staticmethod
    def _extract_text(file_path: str, mime_type: str) -> str:
        if not os.path.exists(file_path):
            return ""

        if mime_type in ["application/pdf", "application/x-pdf"]:
            try:
                import fitz
            except ImportError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PDF support requires PyMuPDF",
                ) from exc

            try:
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                return text
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to extract text from PDF",
                ) from exc

        if mime_type in [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]:
            try:
                from docx import Document
            except ImportError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="DOCX support requires python-docx",
                ) from exc

            try:
                doc = Document(file_path)
                return "\n".join(paragraph.text for paragraph in doc.paragraphs)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to extract text from DOCX",
                ) from exc

        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
            return handle.read()

    def _split_to_chunks(self, text: str, max_chunk_size: int = 1000) -> list[str]:
        chunks: list[str] = []
        current = ""

        for paragraph in text.split("\n"):
            if not paragraph.strip():
                continue
            sentences = paragraph.split(". ")
            for sentence in sentences:
                sentence_text = sentence.strip()
                if not sentence_text:
                    continue

                if len(sentence_text) > max_chunk_size:
                    if current:
                        chunks.append(current.strip())
                        current = ""
                    for i in range(0, len(sentence_text), max_chunk_size):
                        chunks.append(sentence_text[i : i + max_chunk_size])
                    continue

                sentence_with_suffix = f"{sentence_text}. "
                if current and len(current) + len(sentence_with_suffix) <= max_chunk_size:
                    current = f"{current}{sentence_with_suffix}"
                elif not current:
                    if len(sentence_with_suffix) <= max_chunk_size:
                        current = sentence_with_suffix
                    else:
                        current = sentence_text
                else:
                    chunks.append(current.strip())
                    if len(sentence_with_suffix) <= max_chunk_size:
                        current = sentence_with_suffix
                    else:
                        current = sentence_text

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

    def _session(self) -> AsyncSession:
        return self._session_factory()


def get_knowledge_service() -> KnowledgeService:
    """Dependency injection helper for KnowledgeService."""

    return KnowledgeService()
