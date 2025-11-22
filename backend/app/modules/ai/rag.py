"""RAG service stub."""

from app.modules.ai.embeddings import EmbeddingsClient
from app.modules.ai.models import KnowledgeChunk


class RAGService:
    def __init__(self, embeddings_client: EmbeddingsClient | None = None):
        self._embeddings = embeddings_client or EmbeddingsClient()

    async def find_relevant_chunks(self, bot_id: int, question: str, top_k: int = 5, min_similarity: float = 0.3) -> list[KnowledgeChunk]:
        return []
