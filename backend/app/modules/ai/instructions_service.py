"""AI instructions CRUD service."""
from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import async_session_factory
from app.modules.ai.models import AIInstructions
from app.modules.ai.models import utcnow


class AIInstructionsService:
    def __init__(
        self,
        db_session_factory: Callable[[], AsyncSession]
        | async_sessionmaker[AsyncSession]
        | None = None,
    ):
        self._session_factory = db_session_factory or async_session_factory

    model = AIInstructions

    async def get_instructions(self, bot_id: int) -> AIInstructions | None:
        async with self._session() as session:
            result = await session.execute(
                select(AIInstructions).where(AIInstructions.bot_id == bot_id)
            )
            return result.scalars().one_or_none()

    async def upsert_instructions(
        self, bot_id: int, system_prompt: str
    ) -> AIInstructions:
        async with self._session() as session:
            result = await session.execute(
                select(AIInstructions).where(AIInstructions.bot_id == bot_id)
            )
            instruction = result.scalars().one_or_none()

            if instruction:
                instruction.system_prompt = system_prompt
                instruction.updated_at = utcnow()
            else:
                instruction = AIInstructions(
                    bot_id=bot_id, system_prompt=system_prompt
                )
                session.add(instruction)

            await session.commit()
            await session.refresh(instruction)
            return instruction

    async def delete_instruction(self, bot_id: int) -> None:
        async with self._session() as session:
            result = await session.execute(
                select(AIInstructions).where(AIInstructions.bot_id == bot_id)
            )
            instruction = result.scalars().one_or_none()
            if instruction:
                await session.delete(instruction)
                await session.commit()

    async def update_instruction_fields(
        self, instruction: AIInstructions, fields: dict[str, Any]
    ) -> AIInstructions:
        async with self._session() as session:
            instruction = await session.merge(instruction)
            for field, value in fields.items():
                setattr(instruction, field, value)
            instruction.updated_at = utcnow()
            session.add(instruction)
            await session.commit()
            await session.refresh(instruction)
            return instruction

    def _session(self) -> AsyncSession:
        if self._session_factory is None:
            raise RuntimeError("Database session factory is not configured")
        return self._session_factory()
