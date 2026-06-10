"""GigaChat LLM client built on top of async httpx."""
from __future__ import annotations

import base64
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _parse_token_expiry(expires_at: Any, expires_in: Any) -> datetime:
    if isinstance(expires_at, (int, float)) or (
        isinstance(expires_at, str) and expires_at.strip().isdigit()
    ):
        try:
            return datetime.utcfromtimestamp(float(expires_at) / 1000)
        except (OverflowError, TypeError, ValueError):
            pass
    elif expires_at:
        try:
            expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if expiry.tzinfo is not None:
                expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)
            return expiry
        except ValueError:
            pass

    try:
        lifetime_seconds = int(expires_in) if expires_in is not None else 3600
    except (TypeError, ValueError):
        lifetime_seconds = 3600
    return datetime.utcnow() + timedelta(seconds=lifetime_seconds)


class LLMClient:
    """Base interface for LLM clients."""

    async def generate(
        self,
        system_prompt: str,
        history: list[dict[str, str]],
        question: str,
        context_chunks: list[str],
    ) -> str:
        raise NotImplementedError


class OpenAILLMClient(LLMClient):
    """Optional OpenAI LLM client for chat completions."""

    async def generate(
        self,
        system_prompt: str,
        history: list[dict[str, str]],
        question: str,
        context_chunks: list[str],
    ) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        for item in history:
            messages.append(item)

        if context_chunks:
            context_text = "\n".join(context_chunks)
            messages.append(
                {
                    "role": "system",
                    "content": f"Контекст знаний:\n{context_text}",
                }
            )

        messages.append({"role": "user", "content": question})

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key is not configured")
            return ""

        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.warning("openai package is not installed")
            return ""

        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            client = AsyncOpenAI(api_key=api_key)
        model = os.getenv("OPENAI_CHAT_MODEL", "gpt-3.5-turbo")

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
            )
        except Exception as exc:  # pragma: no cover - runtime dependency
            logger.error("LLM generate error", exc_info=exc)
            return ""

        try:
            return (response.choices[0].message.content or "").strip()
        except Exception:  # pragma: no cover - defensive parse
            return ""


class GigaChatLLMClient(LLMClient):
    """Client for the GigaChat chat completion endpoint with token caching."""

    def __init__(
        self, model: str = settings.gigachat_chat_model, timeout: float = 60.0
    ):
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
        data = {"scope": self._scope}

        async with httpx.AsyncClient(verify=self._verify, timeout=self._timeout) as client:
            response = await client.post(self._auth_url, data=data, headers=headers)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        access_token = payload.get("access_token")
        if not access_token:
            raise RuntimeError("Failed to obtain GigaChat access token")

        self._token_expiry = _parse_token_expiry(
            expires_at=payload.get("expires_at"),
            expires_in=payload.get("expires_in"),
        )

        self._token = access_token
        return access_token

    async def generate(
        self,
        system_prompt: str,
        history: list[dict[str, str]],
        question: str,
        context_chunks: list[str],
    ) -> str:
        if not self._api_url:
            raise RuntimeError("GigaChat API URL is not configured")

        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.extend(history)

        user_content = question
        if context_chunks:
            context = "\n\n".join(context_chunks)
            user_content = f"{question}\n\nContext:\n{context}"

        messages.append({"role": "user", "content": user_content})

        payload = {"model": self._model, "messages": messages, "stream": False}

        async with httpx.AsyncClient(
            base_url=self._api_url, verify=self._verify, timeout=self._timeout
        ) as client:
            response = await client.post("/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        choices = data.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return message.get("content", "")
