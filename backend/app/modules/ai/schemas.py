"""AI schemas."""

from datetime import datetime
from typing import List

from pydantic import BaseModel


class AIInstructionIn(BaseModel):
    title: str
    content: str
    is_active: bool = True


class AIInstructionOut(BaseModel):
    id: int
    bot_id: int
    title: str
    content: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeFileOut(BaseModel):
    id: int
    filename: str
    original_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIAnswer(BaseModel):
    can_answer: bool
    answer_text: str | None
    confidence: float
    used_chunk_ids: List[int]
