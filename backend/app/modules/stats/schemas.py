"""Statistics schemas."""
from __future__ import annotations

from pydantic import BaseModel


class DialogStatusBreakdown(BaseModel):
    auto: int = 0
    wait_operator: int = 0
    wait_user: int = 0


class TimingMetrics(BaseModel):
    average_dialog_duration_seconds: float | None = None
    average_time_to_first_message_seconds: float | None = None


class DialogCounts(BaseModel):
    total: int
    active: int
    by_status: DialogStatusBreakdown


class StatsSummary(BaseModel):
    dialogs: DialogCounts
    timing: TimingMetrics


class AdminInfo(BaseModel):
    id: int
    email: str
    full_name: str | None = None


class AdminsStatsResponse(BaseModel):
    admins: list[AdminInfo]
