"""AI schemas for instructions, knowledge base, and question answering."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: list[T]

    model_config = ConfigDict(from_attributes=True)


class AIInstructionsBase(BaseModel):
    system_prompt: str


class AIInstructionsCreate(AIInstructionsBase):
    pass


class AIInstructionsUpdate(BaseModel):
    system_prompt: str | None = None


class AIInstructionsOut(AIInstructionsBase):
    id: int
    bot_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeFileOut(BaseModel):
    id: int
    bot_id: int
    file_name: str
    original_name: str
    mime_type: str | None
    size_bytes: int
    chunks_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeChunkOut(BaseModel):
    id: int
    file_id: int
    bot_id: int
    chunk_index: int
    text: str
    embedding: list
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AskAIRequest(BaseModel):
    question: str
    dialog_id: int | None = None


class AskAIResponse(BaseModel):
    can_answer: bool
    answer_text: str | None = None
    confidence: float
    used_chunk_ids: list[int] = Field(default_factory=list)


class AIAnswer(AskAIResponse):
    """Internal schema mirroring :class:`AskAIResponse` for service returns."""

    model_config = ConfigDict(from_attributes=True)
