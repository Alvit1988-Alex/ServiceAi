"""AI router exposing instructions, knowledge base, and Q&A endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies import get_accessible_bot
from app.modules.accounts.models import User
from app.modules.bots.models import Bot
from app.modules.ai.instructions_service import (
    AIInstructionsService,
    get_ai_instructions_service,
)
from app.modules.ai.knowledge_service import KnowledgeService, get_knowledge_service
from app.modules.ai.schemas import (
    AIAnswer,
    AIInstructionsIn,
    AIInstructionsOut,
    AskAIRequest,
    KnowledgeFileOut,
    ListResponse,
)
from app.modules.ai.service import AIService, get_ai_service
from app.security.auth import get_current_user

router = APIRouter(prefix="/bots/{bot_id}/ai", tags=["ai"])


@router.get("/instructions", response_model=AIInstructionsOut)
async def get_instructions(
    bot_id: int,
    accessible_bot: Bot = Depends(get_accessible_bot),
    current_user: User = Depends(get_current_user),
    service: AIInstructionsService = Depends(get_ai_instructions_service),
) -> AIInstructionsOut:
    instructions = await service.get_instructions(bot_id=accessible_bot.id)
    if not instructions:
        instructions = await service.upsert_instructions(
            bot_id=accessible_bot.id,
            system_prompt="",
        )
    return instructions


@router.put("/instructions", response_model=AIInstructionsOut)
async def upsert_instruction(
    bot_id: int,
    data: AIInstructionsIn,
    accessible_bot: Bot = Depends(get_accessible_bot),
    current_user: User = Depends(get_current_user),
    service: AIInstructionsService = Depends(get_ai_instructions_service),
) -> AIInstructionsOut:
    return await service.upsert_instructions(
        bot_id=accessible_bot.id,
        system_prompt=data.system_prompt,
    )


@router.post(
    "/knowledge/upload",
    response_model=KnowledgeFileOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_knowledge_file(
    bot_id: int,
    accessible_bot: Bot = Depends(get_accessible_bot),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeFileOut:
    return await service.upload_file(bot_id=accessible_bot.id, file=file)


@router.get("/knowledge", response_model=ListResponse[KnowledgeFileOut])
async def list_knowledge_files(
    bot_id: int,
    accessible_bot: Bot = Depends(get_accessible_bot),
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> ListResponse[KnowledgeFileOut]:
    items = await service.list_files(bot_id=accessible_bot.id)
    return ListResponse[KnowledgeFileOut](items=items)


@router.delete("/knowledge/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_file(
    bot_id: int,
    file_id: int,
    accessible_bot: Bot = Depends(get_accessible_bot),
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> None:
    knowledge_file = await service.get_file(bot_id=accessible_bot.id, file_id=file_id)
    if not knowledge_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge file not found"
        )

    await service.delete_file(bot_id=accessible_bot.id, file_id=file_id)


@router.post("/ask", response_model=AIAnswer)
async def ask_ai(
    bot_id: int,
    data: AskAIRequest,
    accessible_bot: Bot = Depends(get_accessible_bot),
    current_user: User = Depends(get_current_user),
    ai_service: AIService = Depends(get_ai_service),
) -> AIAnswer:
    return await ai_service.answer(
        bot_id=accessible_bot.id,
        dialog_id=data.dialog_id,
        question=data.question,
    )
