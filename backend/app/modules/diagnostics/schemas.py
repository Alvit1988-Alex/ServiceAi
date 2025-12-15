"""Pydantic schemas for diagnostics responses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DiagnosticsSummary(BaseModel):
    ok: int
    warn: int
    fail: int


class DiagnosticCheck(BaseModel):
    code: str
    title: str
    status: Literal["ok", "warn", "fail"]
    severity: Literal["fail", "warn", "info"] = "fail"
    account_id: int | None = None
    bot_id: int | None = None
    details: str | None = None


class IntegrationError(BaseModel):
    time: datetime
    account_id: int
    bot_id: int | None = None
    channel_type: str
    operation: str
    message: str

    model_config = ConfigDict(from_attributes=True)


class DiagnosticsResponse(BaseModel):
    summary: DiagnosticsSummary
    checks: list[DiagnosticCheck]
    recent_errors: list[IntegrationError]

