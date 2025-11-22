"""AI instructions CRUD service."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AIInstruction


class AIInstructionsService:
    model = AIInstruction

    async def get_instructions(
        self, session: AsyncSession, bot_id: int, active_only: bool = True
    ) -> list[AIInstruction]:
        stmt = select(AIInstruction).where(AIInstruction.bot_id == bot_id)
        if active_only:
            stmt = stmt.where(AIInstruction.is_active.is_(True))
        result = await session.execute(stmt)
        return result.scalars().all()

    async def upsert_instructions(
        self, session: AsyncSession, bot_id: int, title: str, content: str, is_active: bool
    ) -> AIInstruction:
        stmt = select(AIInstruction).where(
            AIInstruction.bot_id == bot_id, AIInstruction.title == title
        )
        result = await session.execute(stmt)
        instruction = result.scalars().first()

        if instruction:
            instruction.content = content
            instruction.is_active = is_active
        else:
            instruction = AIInstruction(
                bot_id=bot_id,
                title=title,
                content=content,
                is_active=is_active,
            )
            session.add(instruction)

        await session.commit()
        await session.refresh(instruction)
        return instruction

    async def get_instruction(
        self, session: AsyncSession, bot_id: int, instruction_id: int
    ) -> AIInstruction | None:
        result = await session.execute(
            select(AIInstruction).where(
                AIInstruction.bot_id == bot_id, AIInstruction.id == instruction_id
            )
        )
        return result.scalars().first()

    async def delete_instruction(self, session: AsyncSession, bot_id: int, instruction_id: int) -> None:
        result = await session.execute(
            select(AIInstruction).where(
                AIInstruction.bot_id == bot_id, AIInstruction.id == instruction_id
            )
        )
        instruction = result.scalars().first()
        if instruction:
            await session.delete(instruction)
            await session.commit()

    async def update_instruction_fields(
        self, session: AsyncSession, instruction: AIInstruction, fields: dict[str, Any]
    ) -> AIInstruction:
        for field, value in fields.items():
            setattr(instruction, field, value)
        session.add(instruction)
        await session.commit()
        await session.refresh(instruction)
        return instruction
