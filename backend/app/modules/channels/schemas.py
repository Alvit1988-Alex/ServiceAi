"""Channel shared schemas and message normalisation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.modules.channels.models import ChannelType

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: list[T]

    model_config = ConfigDict(from_attributes=True)


class Attachment(BaseModel):
    type: Literal["image", "document", "video", "audio", "other"]
    url: str | None = None
    file_id: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    extra: dict[str, Any] | None = None


class NormalizedMessage(BaseModel):
    bot_id: int
    channel_type: ChannelType
    external_chat_id: str
    external_user_id: str
    text: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)
    timestamp: datetime | None = None
    raw_update: dict[str, Any]


class NormalizedIncomingMessage(BaseModel):
    bot_id: int
    channel_id: int
    channel_type: ChannelType
    external_chat_id: str
    external_user_id: str
    external_message_id: str | None = None
    text: str | None = None
    payload: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class BotChannelBase(BaseModel):
    channel_type: ChannelType
    config: dict[str, Any]
    is_active: bool = True


class BotChannelCreate(BotChannelBase):
    pass


class BotChannelUpdate(BaseModel):
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class BotChannelOut(BaseModel):
    id: int
    bot_id: int
    channel_type: ChannelType
    config: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field(return_type=Literal["ok", "pending", "error"] | None)
    @property
    def webhook_status(self) -> Literal["ok", "pending", "error"] | None:  # type: ignore[override]
        status = (self.config or {}).get("webhook_status")
        if status in {"ok", "pending", "error"}:
            return status
        return None

    @computed_field(return_type=str | None)
    @property
    def webhook_error(self) -> str | None:  # type: ignore[override]
        error = (self.config or {}).get("webhook_error")
        if error:
            return str(error)
        return None
