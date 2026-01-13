"""GigaChat embeddings client built on async httpx."""
from __future__ import annotations

import base64
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingsClient:
    """Base interface for embeddings clients."""

    async def embed_text(self, text: str) -> list[float]:
        if not text:
            return []

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key is not configured")
            return []

        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.warning("openai package is not installed")
            return []

        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            client = AsyncOpenAI(api_key=api_key)
        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

        try:
            response = await client.embeddings.create(model=model, input=text)
        except Exception as exc:  # pragma: no cover - runtime dependency
            logger.error("OpenAI embedding request failed", exc_info=exc)
            return []

        data = getattr(response, "data", None) or []
        if not data:
            logger.error("OpenAI embedding response missing data")
            return []

        embedding = getattr(data[0], "embedding", None)
        if embedding is None:
            return []

        return list(map(float, embedding))

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key is not configured")
            return []

        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.warning("openai package is not installed")
            return []

        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            client = AsyncOpenAI(api_key=api_key)
        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

        try:
            response = await client.embeddings.create(model=model, input=texts)
        except Exception as exc:  # pragma: no cover - runtime dependency
            logger.error("OpenAI embedding batch request failed", exc_info=exc)
            return []

        data = getattr(response, "data", None) or []
        embeddings: list[list[float]] = [[] for _ in texts]
        for item in data:
            index = getattr(item, "index", None)
            embedding = getattr(item, "embedding", None)
            if embedding is None or index is None:
                continue
            if 0 <= index < len(embeddings):
                embeddings[index] = list(map(float, embedding))
        return embeddings


class GigaChatEmbeddingsClient(EmbeddingsClient):
    """Embeddings client using the GigaChat `/embeddings` endpoint."""

    def __init__(self, model: str = "Embeddings", timeout: float = 60.0):
        self._model = model
        self._timeout = timeout
        self._token: str | None = None
        self._token_expiry: datetime | None = None
        self._auth_url = settings.gigachat_auth_url
        self._api_url = settings.gigachat_api_url
        self._scope = settings.gigachat_scope or "GIGACHAT_API_PERS"
        self._verify = (
            settings.gigachat_cert_path
            if settings.gigachat_use_tls_cert and settings.gigachat_cert_path
            else True
        )

    async def _get_access_token(self) -> str:
        if not settings.gigachat_client_id or not settings.gigachat_client_secret:
            raise RuntimeError("GigaChat credentials are not configured")
        if not self._auth_url:
            raise RuntimeError("GigaChat auth URL is not configured")

        if self._token and self._token_expiry and self._token_expiry > datetime.utcnow() + timedelta(seconds=30):
            return self._token

        credentials = f"{settings.gigachat_client_id}:{settings.gigachat_client_secret}"
        auth_header = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
        }
        data = f"scope={self._scope}"

        async with httpx.AsyncClient(verify=self._verify, timeout=self._timeout) as client:
            response = await client.post(self._auth_url, content=data, headers=headers)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        access_token = payload.get("access_token")
        if not access_token:
            raise RuntimeError("Failed to obtain GigaChat access token")

        expires_in = payload.get("expires_in")
        expires_at = payload.get("expires_at")
        if expires_at:
            try:
                self._token_expiry = datetime.fromisoformat(str(expires_at))
            except ValueError:
                self._token_expiry = datetime.utcnow() + timedelta(seconds=int(expires_in or 3600))
        else:
            self._token_expiry = datetime.utcnow() + timedelta(seconds=int(expires_in or 3600))

        self._token = access_token
        return access_token

    async def embed_text(self, text: str) -> list[float]:
        result = await self.embed_many([text])
        return result[0] if result else []

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._api_url:
            raise RuntimeError("GigaChat API URL is not configured")

        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        payload = {"model": self._model, "input": texts}
        async with httpx.AsyncClient(
            base_url=self._api_url, verify=self._verify, timeout=self._timeout
        ) as client:
            response = await client.post("/embeddings", json=payload, headers=headers)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        embeddings: list[list[float]] = []
        for item in data.get("data", []):
            embedding = item.get("embedding")
            if embedding is not None:
                embeddings.append(list(map(float, embedding)))
        return embeddings
