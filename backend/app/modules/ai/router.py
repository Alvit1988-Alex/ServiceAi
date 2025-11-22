"""AI router stubs for instructions and knowledge base."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.modules.accounts.models import User
from app.modules.ai.schemas import (
    AIInstructionCreate,
    AIInstructionOut,
    AIInstructionUpdate,
    AskAIRequest,
    AskAIResponse,
    KnowledgeFileOut,
    ListResponse,
)
from app.modules.ai.instructions_service import AIInstructionsService
from app.modules.ai.knowledge_service import KnowledgeService
from app.modules.ai.service import AIService, get_ai_service
from app.security.auth import get_current_user

router = APIRouter(prefix="/bots/{bot_id}/ai", tags=["ai"])


@router.get("/instructions", response_model=ListResponse[AIInstructionOut])
async def get_instructions(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: AIInstructionsService = Depends(AIInstructionsService),
) -> ListResponse[AIInstructionOut]:
    items = await service.get_instructions(session=session, bot_id=bot_id)
    return ListResponse[AIInstructionOut](items=items)


@router.post(
    "/instructions", response_model=AIInstructionOut, status_code=status.HTTP_201_CREATED
)
async def create_instruction(
    bot_id: int,
    data: AIInstructionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: AIInstructionsService = Depends(AIInstructionsService),
) -> AIInstructionOut:
    return await service.upsert_instructions(
        session=session,
        bot_id=bot_id,
        title=data.title,
        content=data.content,
        is_active=data.is_active,
    )


@router.patch("/instructions/{instruction_id}", response_model=AIInstructionOut)
async def update_instruction(
    bot_id: int,
    instruction_id: int,
    data: AIInstructionUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: AIInstructionsService = Depends(AIInstructionsService),
) -> AIInstructionOut:
    instruction = await service.get_instruction(
        session=session, bot_id=bot_id, instruction_id=instruction_id
    )
    if not instruction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instruction not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return instruction

    return await service.update_instruction_fields(
        session=session, instruction=instruction, fields=update_data
    )


@router.delete("/instructions/{instruction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instruction(
    bot_id: int,
    instruction_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: AIInstructionsService = Depends(AIInstructionsService),
) -> None:
    instruction = await service.get_instruction(
        session=session, bot_id=bot_id, instruction_id=instruction_id
    )
    if not instruction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instruction not found")

    await service.delete_instruction(
        session=session, bot_id=bot_id, instruction_id=instruction_id
    )


@router.get("/knowledge", response_model=ListResponse[KnowledgeFileOut])
async def list_knowledge_files(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: KnowledgeService = Depends(KnowledgeService),
) -> ListResponse[KnowledgeFileOut]:
    items = await service.list_files(session=session, bot_id=bot_id)
    return ListResponse[KnowledgeFileOut](items=items)


@router.post(
    "/knowledge", response_model=KnowledgeFileOut, status_code=status.HTTP_201_CREATED
)
async def upload_knowledge_file(
    bot_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: KnowledgeService = Depends(KnowledgeService),
) -> KnowledgeFileOut:
    return await service.upload_file(session=session, bot_id=bot_id, file=file)


@router.delete("/knowledge/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_file(
    bot_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: KnowledgeService = Depends(KnowledgeService),
) -> None:
    knowledge_file = await service.get_file(session=session, bot_id=bot_id, file_id=file_id)
    if not knowledge_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge file not found")

    await service.delete_file(session=session, bot_id=bot_id, file_id=file_id)


@router.post("/ask", response_model=AskAIResponse)
async def ask_ai(
    bot_id: int,
    data: AskAIRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    ai_service: AIService = Depends(get_ai_service),
) -> AskAIResponse:
    return await ai_service.answer(
        session=session,
        bot_id=bot_id,
        dialog_id=data.dialog_id,
        question=data.question,
    )
