from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BitrixConnectRequest(BaseModel):
    bot_id: int = Field(gt=0)
    portal_domain: str = Field(min_length=3)


class BitrixConnectResponse(BaseModel):
    auth_url: str


class BitrixStatusResponse(BaseModel):
    connected: bool
    enabled: bool
    portal_url: str | None = None
    connected_at: datetime | None = None
    openline_id: str | None = None
    auto_create_lead_on_first_message: bool = True


class BitrixDisconnectRequest(BaseModel):
    bot_id: int = Field(gt=0)


class BitrixSettingsUpdateRequest(BaseModel):
    bot_id: int = Field(gt=0)
    openline_id: str | None = None
    auto_create_lead_on_first_message: bool


class BitrixEventPayload(BaseModel):
    event: str | None = None
    data: dict | None = None
    auth: dict | None = None
