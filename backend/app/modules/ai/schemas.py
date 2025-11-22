"""AI schemas for instructions, knowledge base, and question answering."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: list[T]

    model_config = ConfigDict(from_attributes=True)


class AIInstructionsIn(BaseModel):
    system_prompt: str


class AIInstructionsOut(BaseModel):
    id: int
    bot_id: int
    system_prompt: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeFileOut(BaseModel):
    id: int
    bot_id: int
    file_name: str
    original_name: str
    size_bytes: int
    mime_type: str | None
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


class AIAnswer(BaseModel):
    can_answer: bool
    answer: str | None = None
    confidence: float
    used_chunk_ids: list[int] = Field(default_factory=list)
