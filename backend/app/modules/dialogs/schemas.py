"""Dialog schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from app.modules.dialogs.models import DialogStatus, MessageSender

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: list[T]

    model_config = ConfigDict(from_attributes=True)


class DialogBase(BaseModel):
    user_external_id: str
    status: DialogStatus = DialogStatus.AUTO
    closed: bool = False


class DialogCreate(DialogBase):
    bot_id: int


class DialogUpdate(BaseModel):
    status: DialogStatus | None = None
    closed: bool | None = None


class DialogOut(DialogBase):
    id: int
    bot_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DialogMessageBase(BaseModel):
    sender: MessageSender
    text: str | None = None
    payload: dict | None = None


class DialogMessageCreate(DialogMessageBase):
    dialog_id: int


class DialogMessageOut(DialogMessageBase):
    id: int
    dialog_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
