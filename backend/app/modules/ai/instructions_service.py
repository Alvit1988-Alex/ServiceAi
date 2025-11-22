"""AI instructions service stub."""

from app.modules.ai.models import AIInstructions


class AIInstructionsService:
    async def get_instructions(self, bot_id: int) -> AIInstructions | None:
        return None

    async def upsert_instructions(self, bot_id: int, system_prompt: str) -> AIInstructions:
        inst = AIInstructions(id=0, bot_id=bot_id, system_prompt=system_prompt)
        return inst
