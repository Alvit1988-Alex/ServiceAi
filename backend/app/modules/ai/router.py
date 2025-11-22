"""AI router stubs for instructions and knowledge base."""

from fastapi import APIRouter

from app.modules.ai.schemas import AIInstructionIn, AIInstructionOut, KnowledgeFileOut
from app.modules.ai.instructions_service import AIInstructionsService
from app.modules.ai.knowledge_service import KnowledgeService

router = APIRouter(prefix="/bots/{bot_id}/ai", tags=["ai"])


@router.get("/instructions", response_model=list[AIInstructionOut])
async def get_instructions(
    bot_id: int, service: AIInstructionsService = AIInstructionsService()
):
    return await service.get_instructions(bot_id)


@router.put("/instructions", response_model=AIInstructionOut)
async def update_instructions(
    bot_id: int, data: AIInstructionIn, service: AIInstructionsService = AIInstructionsService()
):
    return await service.upsert_instructions(
        bot_id=bot_id, title=data.title, content=data.content, is_active=data.is_active
    )


@router.get("/knowledge", response_model=list[KnowledgeFileOut])
async def list_knowledge_files(
    bot_id: int, service: KnowledgeService = KnowledgeService()
):
    return await service.list_files(bot_id)
