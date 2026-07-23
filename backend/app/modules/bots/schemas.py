"""Bot schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.bots.models import BotAdminRole

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: list[T]

    model_config = ConfigDict(from_attributes=True)


MAX_OPERATOR_TRIGGER_PHRASES = 100
MAX_OPERATOR_TRIGGER_PHRASE_LENGTH = 200


def normalize_operator_trigger_phrases(value: list[str]) -> list[str]:
    phrases: list[str] = []
    seen: set[str] = set()
    for phrase in value:
        phrase = phrase.strip()
        if not phrase:
            continue
        if len(phrase) > MAX_OPERATOR_TRIGGER_PHRASE_LENGTH:
            raise ValueError("operator trigger phrase is too long")
        key = phrase.casefold()
        if key in seen:
            continue
        seen.add(key)
        phrases.append(phrase)
    if len(phrases) > MAX_OPERATOR_TRIGGER_PHRASES:
        raise ValueError("operator trigger phrases limit exceeded")
    return phrases


class BotBase(BaseModel):
    name: str
    description: str | None = None
    operator_handoff_enabled: bool = False
    operator_trigger_phrases: list[str] = Field(default_factory=list)

    @field_validator("operator_trigger_phrases")
    @classmethod
    def validate_operator_trigger_phrases(cls, value: list[str]) -> list[str]:
        return normalize_operator_trigger_phrases(value)


class BotCreate(BotBase):
    pass


class BotCreateInternal(BotBase):
    account_id: int


class BotUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    operator_handoff_enabled: bool | None = None
    operator_trigger_phrases: list[str] | None = None

    @field_validator("operator_handoff_enabled", "operator_trigger_phrases")
    @classmethod
    def reject_null_operator_settings(cls, value: object) -> object:
        if value is None:
            raise ValueError("operator handoff fields cannot be null")
        return value

    @field_validator("operator_trigger_phrases")
    @classmethod
    def validate_update_operator_trigger_phrases(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return normalize_operator_trigger_phrases(value)


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
