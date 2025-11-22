"""Knowledge base service for storing files and embedding their content."""
from __future__ import annotations

from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BASE_DIR
from app.modules.ai.embeddings import EmbeddingsClient, GigaChatEmbeddingsClient
from app.modules.ai.models import KnowledgeChunk, KnowledgeFile


class KnowledgeService:
    def __init__(self, embeddings_client: EmbeddingsClient | None = None):
        self._embeddings = embeddings_client or GigaChatEmbeddingsClient()
        self._storage_dir = BASE_DIR / "data" / "knowledge"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(self, session: AsyncSession, bot_id: int, file: UploadFile) -> KnowledgeFile:
        content_bytes = await file.read()
        filename = f"{uuid4().hex}_{file.filename}"
        file_path = self._storage_dir / filename
        file_path.write_bytes(content_bytes)

        text_content = content_bytes.decode(errors="ignore")
        chunks = self._chunk_text(text_content)
        embeddings = await self._embeddings.embed_many(chunks) if chunks else []

        knowledge_file = KnowledgeFile(
            bot_id=bot_id,
            filename=filename,
            original_name=file.filename or "file",
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=len(content_bytes),
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
                    content=chunk_text,
                    metadata_={"chunk_index": idx},
                    embedding=embedding,
                )
            )

        session.add_all(knowledge_chunks)
        await session.commit()
        await session.refresh(knowledge_file)
        return knowledge_file

    async def list_files(self, session: AsyncSession, bot_id: int) -> list[KnowledgeFile]:
        result = await session.execute(
            select(KnowledgeFile).where(KnowledgeFile.bot_id == bot_id)
        )
        return result.scalars().all()

    async def delete_file(self, session: AsyncSession, bot_id: int, file_id: int) -> None:
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

        stored_path = self._storage_dir / knowledge_file.filename
        if stored_path.exists():
            stored_path.unlink()

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
