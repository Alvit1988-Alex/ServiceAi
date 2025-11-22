"""Pydantic schemas for accounts and users."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.accounts.models import UserRole

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: list[T]

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    role: UserRole
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = None


class UserOut(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountBase(BaseModel):
    name: str


class AccountCreate(AccountBase):
    owner_id: int
    operator_ids: list[int] | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    owner_id: int | None = None
    operator_ids: list[int] | None = None


class AccountOut(AccountBase):
    id: int
    owner_id: int
    operators: list[UserOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
