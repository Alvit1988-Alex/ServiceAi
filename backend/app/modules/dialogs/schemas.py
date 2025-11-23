"""Dialog schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from app.modules.channels.models import ChannelType
from app.modules.dialogs.models import DialogStatus, MessageSender

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    per_page: int
    total: int
    has_next: bool

    model_config = ConfigDict(from_attributes=True)


class DialogBase(BaseModel):
    channel_type: ChannelType
    external_chat_id: str
    external_user_id: str
    status: DialogStatus = DialogStatus.AUTO
    closed: bool = False


class DialogCreate(DialogBase):
    bot_id: int


class DialogUpdate(BaseModel):
    status: DialogStatus | None = None
    closed: bool | None = None
    assigned_admin_id: int | None = None
    is_locked: bool | None = None
    locked_until: datetime | None = None
    unread_messages_count: int | None = None
    waiting_time_seconds: int | None = None


class DialogOut(DialogBase):
    id: int
    bot_id: int
    last_message_at: datetime
    unread_messages_count: int
    is_locked: bool
    locked_until: datetime | None
    assigned_admin_id: int | None
    waiting_time_seconds: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DialogShort(DialogOut):
    last_message: "DialogMessageOut | None" = None

    model_config = ConfigDict(from_attributes=True)


class DialogDetail(DialogOut):
    messages: list["DialogMessageOut"]

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
