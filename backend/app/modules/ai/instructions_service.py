"""AI instructions service stub."""

from app.modules.ai.models import AIInstruction


class AIInstructionsService:
    async def get_instructions(self, bot_id: int) -> list[AIInstruction]:
        return []

    async def upsert_instructions(
        self, bot_id: int, title: str, content: str, is_active: bool
    ) -> AIInstruction:
        instruction = AIInstruction(
            id=0,
            bot_id=bot_id,
            title=title,
            content=content,
            is_active=is_active,
        )
        return instruction
