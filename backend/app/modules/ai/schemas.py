"""AI schemas for instructions, knowledge base, and question answering."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: list[T]

    model_config = ConfigDict(from_attributes=True)


class AIInstructionBase(BaseModel):
    title: str
    content: str
    is_active: bool = True


class AIInstructionCreate(AIInstructionBase):
    pass


class AIInstructionUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    is_active: bool | None = None


class AIInstructionOut(AIInstructionBase):
    id: int
    bot_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeFileOut(BaseModel):
    id: int
    bot_id: int
    filename: str
    original_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeChunkOut(BaseModel):
    id: int
    file_id: int
    bot_id: int
    content: str
    metadata: dict | None = Field(default=None, validation_alias="metadata_", serialization_alias="metadata")
    embedding: list | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AskAIRequest(BaseModel):
    question: str
    dialog_id: int | None = None


class AskAIResponse(BaseModel):
    can_answer: bool
    answer_text: str | None = None
    confidence: float
    used_chunk_ids: list[int] = Field(default_factory=list)
