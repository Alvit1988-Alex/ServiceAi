"""AI router stubs for instructions and knowledge base."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from app.modules.accounts.models import User
from app.modules.ai.schemas import (
    AIAnswer,
    AIInstructionsIn,
    AIInstructionsOut,
    AskAIRequest,
    KnowledgeFileOut,
    ListResponse,
)
from app.modules.ai.instructions_service import AIInstructionsService
from app.modules.ai.knowledge_service import KnowledgeService
from app.modules.ai.service import AIService, get_ai_service
from app.security.auth import get_current_user

router = APIRouter(prefix="/bots/{bot_id}/ai", tags=["ai"])


@router.get("/instructions", response_model=AIInstructionsOut)
async def get_instructions(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    service: AIInstructionsService = Depends(AIInstructionsService),
) -> AIInstructionsOut:
    instructions = await service.get_instructions(bot_id=bot_id)
    if not instructions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instructions not found")
    return instructions


@router.post(
    "/instructions", response_model=AIInstructionsOut, status_code=status.HTTP_201_CREATED
)
async def create_instruction(
    bot_id: int,
    data: AIInstructionsIn,
    current_user: User = Depends(get_current_user),
    service: AIInstructionsService = Depends(AIInstructionsService),
) -> AIInstructionsOut:
    return await service.upsert_instructions(
        bot_id=bot_id,
        system_prompt=data.system_prompt,
    )


@router.patch("/instructions", response_model=AIInstructionsOut)
async def update_instruction(
    bot_id: int,
    data: AIInstructionsIn,
    current_user: User = Depends(get_current_user),
    service: AIInstructionsService = Depends(AIInstructionsService),
) -> AIInstructionsOut:
    instruction = await service.get_instructions(bot_id=bot_id)
    if not instruction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instructions not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return instruction

    return await service.update_instruction_fields(
        instruction=instruction, fields=update_data
    )


@router.delete("/instructions", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instruction(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    service: AIInstructionsService = Depends(AIInstructionsService),
) -> None:
    instruction = await service.get_instructions(bot_id=bot_id)
    if not instruction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instruction not found")

    await service.delete_instruction(bot_id=bot_id)


@router.get("/knowledge", response_model=ListResponse[KnowledgeFileOut])
async def list_knowledge_files(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(KnowledgeService),
) -> ListResponse[KnowledgeFileOut]:
    items = await service.list_files(bot_id=bot_id)
    return ListResponse[KnowledgeFileOut](items=items)


@router.post(
    "/knowledge", response_model=KnowledgeFileOut, status_code=status.HTTP_201_CREATED
)
async def upload_knowledge_file(
    bot_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(KnowledgeService),
) -> KnowledgeFileOut:
    return await service.upload_file(bot_id=bot_id, file=file)


@router.delete("/knowledge/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_file(
    bot_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(KnowledgeService),
) -> None:
    knowledge_file = await service.get_file(bot_id=bot_id, file_id=file_id)
    if not knowledge_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge file not found")

    await service.delete_file(bot_id=bot_id, file_id=file_id)


@router.post("/ask", response_model=AIAnswer)
async def ask_ai(
    bot_id: int,
    data: AskAIRequest,
    current_user: User = Depends(get_current_user),
    ai_service: AIService = Depends(get_ai_service),
) -> AIAnswer:
    return await ai_service.answer(
        bot_id=bot_id,
        dialog_id=data.dialog_id,
        question=data.question,
    )
