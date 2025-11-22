"""Embeddings client stub."""


class EmbeddingsClient:
    async def embed_text(self, text: str) -> list[float]:
        return [0.0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]
