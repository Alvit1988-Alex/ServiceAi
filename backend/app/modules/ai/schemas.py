"""AI schemas."""

from datetime import datetime
from typing import List

from pydantic import BaseModel


class AIInstructionsIn(BaseModel):
    system_prompt: str


class AIInstructionsOut(BaseModel):
    bot_id: int
    system_prompt: str
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class KnowledgeFileOut(BaseModel):
    id: int
    file_name: str
    original_name: str
    size_bytes: int
    chunks_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class AIAnswer(BaseModel):
    can_answer: bool
    answer_text: str | None
    confidence: float
    used_chunk_ids: List[int]
