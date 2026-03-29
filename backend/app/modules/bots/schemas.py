"""Bot schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.modules.bots.models import BotAdminRole

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: list[T]

    model_config = ConfigDict(from_attributes=True)


class BotBase(BaseModel):
    name: str
    description: str | None = None


class BotCreate(BotBase):
    pass


class BotCreateInternal(BotBase):
    account_id: int


class BotUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class BotOut(BotBase):
    id: int
    account_id: int
    is_owned: bool = True
    access_role: str = "owner"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BotAdminOut(BaseModel):
    id: int
    bot_id: int
    user_id: int
    role: BotAdminRole
    account_public_id: str
    first_name: str | None = None
    last_name: str | None = None


class BotAdminCreate(BaseModel):
    account_public_id: str = Field(min_length=8, max_length=8)
    role: BotAdminRole = BotAdminRole.admin


class BotAdminDelete(BaseModel):
    user_id: int
