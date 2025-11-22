"""Bot schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: list[T]

    model_config = ConfigDict(from_attributes=True)


class BotBase(BaseModel):
    name: str
    description: str | None = None


class BotCreate(BotBase):
    account_id: int


class BotUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class BotOut(BotBase):
    id: int
    account_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
