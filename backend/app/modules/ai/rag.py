"""RAG service for retrieving relevant knowledge chunks."""
from __future__ import annotations

import logging
import math
from typing import Callable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.database import async_session_factory
from app.modules.ai.embeddings import EmbeddingsClient, GigaChatEmbeddingsClient
from app.modules.ai.models import KnowledgeChunk

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(
        self,
        db_session_factory: Callable[[], AsyncSession]
        | async_sessionmaker[AsyncSession]
        | None = None,
        embeddings_client: EmbeddingsClient | None = None,
    ):
        self._session_factory = db_session_factory or async_session_factory
        if embeddings_client is not None:
            self._embeddings = embeddings_client
        elif settings.ai_embeddings_provider == "openai":
            self._embeddings = EmbeddingsClient()
        elif settings.ai_embeddings_provider == "gigachat":
            self._embeddings = GigaChatEmbeddingsClient(
                model=settings.gigachat_embedding_model
            )
        else:
            logger.warning(
                "Unknown AI embeddings provider %r; falling back to GigaChat",
                settings.ai_embeddings_provider,
            )
            self._embeddings = GigaChatEmbeddingsClient(
                model=settings.gigachat_embedding_model
            )

    async def find_relevant_chunks(
        self,
        bot_id: int,
        question: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> list[tuple[KnowledgeChunk, float]]:
        """Embed the question, score stored chunks, and return the most relevant."""

        query_embedding = await self._embeddings.embed_text(question)
        if not query_embedding:
            return []

        async with self._session() as session:
            result = await session.execute(
                select(KnowledgeChunk).where(
                    KnowledgeChunk.bot_id == bot_id, KnowledgeChunk.embedding.isnot(None)
                )
            )
            chunks: Sequence[KnowledgeChunk] = result.scalars().all()

        scored: list[tuple[KnowledgeChunk, float]] = []
        for chunk in chunks:
            if not chunk.embedding:
                continue
            similarity = self._cosine_similarity(query_embedding, chunk.embedding)
            if similarity >= min_similarity:
                scored.append((chunk, similarity))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    async def has_knowledge(self, bot_id: int) -> bool:
        async with self._session() as session:
            result = await session.execute(
                select(KnowledgeChunk.id).where(KnowledgeChunk.bot_id == bot_id).limit(1)
            )
            return result.scalar_one_or_none() is not None

    @staticmethod
    def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(float(a) * float(b) for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(float(a) ** 2 for a in vec_a))
        norm_b = math.sqrt(sum(float(b) ** 2 for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _session(self) -> AsyncSession:
        return self._session_factory()
