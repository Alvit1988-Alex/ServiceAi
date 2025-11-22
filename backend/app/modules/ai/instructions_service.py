"""AI instructions CRUD service."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AIInstructions


class AIInstructionsService:
    model = AIInstructions

    async def get_instructions(
        self, session: AsyncSession, bot_id: int
    ) -> AIInstructions | None:
        result = await session.execute(
            select(AIInstructions).where(AIInstructions.bot_id == bot_id)
        )
        return result.scalars().first()

    async def upsert_instructions(
        self, session: AsyncSession, bot_id: int, system_prompt: str
    ) -> AIInstructions:
        result = await session.execute(
            select(AIInstructions).where(AIInstructions.bot_id == bot_id)
        )
        instruction = result.scalars().first()

        if instruction:
            instruction.system_prompt = system_prompt
        else:
            instruction = AIInstructions(bot_id=bot_id, system_prompt=system_prompt)
            session.add(instruction)

        await session.commit()
        await session.refresh(instruction)
        return instruction

    async def delete_instruction(self, session: AsyncSession, bot_id: int) -> None:
        result = await session.execute(
            select(AIInstructions).where(AIInstructions.bot_id == bot_id)
        )
        instruction = result.scalars().first()
        if instruction:
            await session.delete(instruction)
            await session.commit()

    async def update_instruction_fields(
        self, session: AsyncSession, instruction: AIInstructions, fields: dict[str, Any]
    ) -> AIInstructions:
        for field, value in fields.items():
            setattr(instruction, field, value)
        session.add(instruction)
        await session.commit()
        await session.refresh(instruction)
        return instruction
