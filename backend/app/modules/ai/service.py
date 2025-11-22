"""AI service integrating instructions, RAG and LLM."""
from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.instructions_service import AIInstructionsService
from app.modules.ai.llm import GigaChatLLMClient, LLMClient
from app.modules.ai.rag import RAGService
from app.modules.ai.schemas import AIAnswer
from app.modules.dialogs.models import DialogMessage, MessageSender


class AIService:
    def __init__(
        self,
        instructions_service: AIInstructionsService | None = None,
        rag_service: RAGService | None = None,
        llm_client: LLMClient | None = None,
    ):
        self._instructions_service = instructions_service or AIInstructionsService()
        self._rag_service = rag_service or RAGService()
        self._llm_client = llm_client or GigaChatLLMClient()

    async def generate_answer(
        self,
        session: AsyncSession,
        bot_id: int,
        dialog_id: int | None,
        user_message: str,
        hint_mode: bool = False,
    ) -> AIAnswer:
        instructions = await self._instructions_service.get_instructions(
            session=session, bot_id=bot_id, active_only=True
        )
        system_prompt = self._build_system_prompt(instructions, hint_mode)

        history = await self._load_history(session=session, dialog_id=dialog_id)

        relevant_chunks = await self._rag_service.find_relevant_chunks(
            session=session, bot_id=bot_id, question=user_message
        )
        chunk_texts = [chunk.content for chunk, _ in relevant_chunks]
        used_chunk_ids = [chunk.id for chunk, _ in relevant_chunks]
        confidence = max((score for _, score in relevant_chunks), default=0.0)

        answer_text = await self._llm_client.generate(
            system_prompt=system_prompt,
            history=history,
            question=user_message,
            context_chunks=chunk_texts,
        )

        can_answer = bool(answer_text)
        return AIAnswer(
            can_answer=can_answer,
            answer_text=answer_text or None,
            confidence=confidence,
            used_chunk_ids=used_chunk_ids,
        )

    async def _load_history(
        self, session: AsyncSession, dialog_id: int | None, limit: int = 10
    ) -> list[dict[str, str]]:
        if dialog_id is None:
            return []

        result = await session.execute(
            select(DialogMessage)
            .where(DialogMessage.dialog_id == dialog_id, DialogMessage.text.isnot(None))
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
    def _build_system_prompt(instructions: Iterable, hint_mode: bool) -> str:
        instructions_text = "\n".join(
            f"- {instr.title}: {instr.content}" for instr in instructions if instr.is_active
        )
        base_prompt = "You are a helpful assistant. Use provided instructions and context to answer."
        if instructions_text:
            base_prompt = f"{base_prompt}\nInstructions:\n{instructions_text}"
        if hint_mode:
            base_prompt = f"{base_prompt}\nRespond with short hints rather than full answers."
        return base_prompt


def get_ai_service() -> AIService:
    """Factory for dependency injection."""

    return AIService()
