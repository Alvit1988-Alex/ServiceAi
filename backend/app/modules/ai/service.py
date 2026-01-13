"""AI service integrating instructions, RAG and LLM."""
from __future__ import annotations

import logging
import os
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import async_session_factory
from app.modules.ai.instructions_service import AIInstructionsService
from app.modules.ai.models import AIInstructions
from app.modules.ai.llm import GigaChatLLMClient, LLMClient, OpenAILLMClient
from app.modules.ai.rag import RAGService
from app.modules.ai.schemas import AIAnswer
from app.modules.dialogs.models import DialogMessage, MessageSender

logger = logging.getLogger(__name__)
_AI_DISABLED_LOGGED = False


class AIService:
    def __init__(
        self,
        db_session_factory: Callable[[], AsyncSession]
        | async_sessionmaker[AsyncSession]
        | None = None,
        instructions_service: AIInstructionsService | None = None,
        rag_service: RAGService | None = None,
        llm_client: LLMClient | None = None,
    ):
        self._session_factory = db_session_factory or async_session_factory
        self._instructions_service = instructions_service or AIInstructionsService(
            db_session_factory=self._session_factory
        )
        self._rag_service = rag_service or RAGService(
            db_session_factory=self._session_factory
        )
        if llm_client is not None:
            self._llm_client = llm_client
        else:
            if os.getenv("OPENAI_API_KEY"):
                self._llm_client = OpenAILLMClient()
            else:
                self._llm_client = GigaChatLLMClient()
        self._confidence_threshold = 0.35

    async def generate_answer(
        self,
        bot_id: int,
        dialog_id: int | None,
        user_message: str,
        hint_mode: bool = False,
    ) -> AIAnswer:
        instructions = await self._instructions_service.get_instructions(bot_id=bot_id)
        system_prompt = self._build_system_prompt(instructions, hint_mode)

        history = await self._load_history(dialog_id=dialog_id)

        knowledge_enabled = await self._rag_service.has_knowledge(bot_id)
        strict_guard_enabled = knowledge_enabled or (
            instructions is not None
            and (instructions.system_prompt or "").strip() != ""
        )

        if not strict_guard_enabled:
            try:
                answer_text = await self._llm_client.generate(
                    system_prompt=system_prompt,
                    history=history,
                    question=user_message,
                    context_chunks=[],
                )
            except RuntimeError as exc:
                self._log_ai_disabled(exc)
                return AIAnswer(
                    can_answer=False,
                    answer=None,
                    confidence=0.0,
                    used_chunk_ids=[],
                )
            return AIAnswer(
                can_answer=bool(answer_text),
                answer=answer_text or None,
                confidence=0.0,
                used_chunk_ids=[],
            )

        if knowledge_enabled:
            try:
                relevant_chunks = await self._rag_service.find_relevant_chunks(
                    bot_id=bot_id, question=user_message
                )
            except RuntimeError as exc:
                self._log_ai_disabled(exc)
                return AIAnswer(
                    can_answer=False,
                    answer=None,
                    confidence=0.0,
                    used_chunk_ids=[],
                )
            if not relevant_chunks:
                return AIAnswer(
                    can_answer=False,
                    answer=None,
                    confidence=0.0,
                    used_chunk_ids=[],
                )
            chunk_texts = [chunk.text for chunk, _ in relevant_chunks]
            used_chunk_ids = [chunk.id for chunk, _ in relevant_chunks]
            confidence = max((score for _, score in relevant_chunks), default=0.0)

            try:
                answer_text = await self._llm_client.generate(
                    system_prompt=system_prompt,
                    history=history,
                    question=user_message,
                    context_chunks=chunk_texts,
                )
            except RuntimeError as exc:
                self._log_ai_disabled(exc)
                return AIAnswer(
                    can_answer=False,
                    answer=None,
                    confidence=confidence,
                    used_chunk_ids=used_chunk_ids,
                )

            can_answer = bool(answer_text) and confidence >= self._confidence_threshold
            return AIAnswer(
                can_answer=can_answer,
                answer=answer_text if can_answer else None,
                confidence=confidence,
                used_chunk_ids=used_chunk_ids,
            )

        try:
            answer_text = await self._llm_client.generate(
                system_prompt=system_prompt,
                history=history,
                question=user_message,
                context_chunks=[],
            )
        except RuntimeError as exc:
            self._log_ai_disabled(exc)
            return AIAnswer(
                can_answer=False,
                answer=None,
                confidence=0.0,
                used_chunk_ids=[],
            )
        return AIAnswer(
            can_answer=bool(answer_text),
            answer=answer_text or None,
            confidence=0.0,
            used_chunk_ids=[],
        )

    async def answer(
        self,
        bot_id: int,
        dialog_id: int | None,
        question: str,
        hint_mode: bool = False,
    ) -> AIAnswer:
        """Public wrapper for generating an answer to a user's question."""

        return await self.generate_answer(
            bot_id=bot_id,
            dialog_id=dialog_id,
            user_message=question,
            hint_mode=hint_mode,
        )

    async def _load_history(
        self, dialog_id: int | None, limit: int = 10
    ) -> list[dict[str, str]]:
        if dialog_id is None:
            return []

        async with self._session() as session:
            result = await session.execute(
                select(DialogMessage)
                .where(
                    DialogMessage.dialog_id == dialog_id, DialogMessage.text.isnot(None)
                )
                .order_by(DialogMessage.created_at.desc())
                .limit(limit)
            )
            messages: list[DialogMessage] = list(result.scalars().all())
        messages.reverse()

        history: list[dict[str, str]] = []
        for message in messages:
            if message.text is None:
                continue
            role = "assistant" if message.sender == MessageSender.BOT else "user"
            history.append({"role": role, "content": message.text})
        return history

    @staticmethod
    def _build_system_prompt(instructions: AIInstructions | None, hint_mode: bool) -> str:
        base_prompt = "You are a helpful assistant. Use provided instructions and context to answer."
        if instructions and instructions.system_prompt:
            base_prompt = instructions.system_prompt
        if hint_mode:
            base_prompt = f"{base_prompt}\nRespond with short hints rather than full answers."
        return base_prompt

    def _session(self) -> AsyncSession:
        return self._session_factory()

    def _log_ai_disabled(self, exc: Exception) -> None:
        global _AI_DISABLED_LOGGED
        if _AI_DISABLED_LOGGED:
            return
        _AI_DISABLED_LOGGED = True
        logger.info("AI is not configured; falling back to operator mode. %s", exc)


def get_ai_service() -> AIService:
    """Factory for dependency injection."""

    return AIService()
