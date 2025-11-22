"""Channel shared schemas and message normalisation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP_GREEN = "whatsapp_green"
    WHATSAPP_360 = "whatsapp_360"
    WHATSAPP_CUSTOM = "whatsapp_custom"
    AVITO = "avito"
    MAX = "max"
    WEBCHAT = "webchat"


class AttachmentType(str, Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"


class Attachment(BaseModel):
    type: AttachmentType
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
    attachments: list[Attachment] = []
    timestamp: datetime
    raw_update: dict[str, Any]


class BotChannelConfigIn(BaseModel):
    config: dict[str, Any]


class BotChannelOut(BaseModel):
    bot_id: int
    type: ChannelType
    is_enabled: bool

    class Config:
        from_attributes = True
