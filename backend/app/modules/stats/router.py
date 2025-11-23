"""Statistics router implementation."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db_session
from app.modules.accounts.models import Account, User
from app.modules.bots.models import Bot
from app.modules.dialogs.models import Dialog, DialogMessage, DialogStatus
from app.modules.stats.schemas import AdminInfo, AdminsStatsResponse, DialogStatusBreakdown, StatsSummary
from app.security.auth import get_current_user


router = APIRouter(prefix="/bots/{bot_id}/stats", tags=["stats"])


def _calculate_average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


@router.get("/summary", response_model=StatsSummary)
async def get_summary(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StatsSummary:
    total_dialogs = await session.scalar(
        select(func.count(Dialog.id)).where(Dialog.bot_id == bot_id)
    )
    active_dialogs = await session.scalar(
        select(func.count(Dialog.id)).where(Dialog.bot_id == bot_id, Dialog.closed.is_(False))
    )

    status_counts: dict[DialogStatus, int] = defaultdict(int)
    status_rows = await session.execute(
        select(Dialog.status, func.count(Dialog.id)).where(Dialog.bot_id == bot_id).group_by(Dialog.status)
    )
    for status, count in status_rows.all():
        status_counts[status] = count

    dialog_status_breakdown = DialogStatusBreakdown(
        auto=status_counts.get(DialogStatus.AUTO, 0),
        wait_operator=status_counts.get(DialogStatus.WAIT_OPERATOR, 0),
        wait_user=status_counts.get(DialogStatus.WAIT_USER, 0),
    )

    message_stats_rows = await session.execute(
        select(
            DialogMessage.dialog_id,
            func.min(DialogMessage.created_at),
            func.max(DialogMessage.created_at),
            Dialog.created_at,
        )
        .join(Dialog, DialogMessage.dialog_id == Dialog.id)
        .where(Dialog.bot_id == bot_id)
        .group_by(DialogMessage.dialog_id, Dialog.created_at)
    )

    dialog_durations: list[float] = []
    first_message_delays: list[float] = []
    for _dialog_id, first_message_at, last_message_at, dialog_created_at in message_stats_rows.all():
        if isinstance(first_message_at, datetime) and isinstance(last_message_at, datetime):
            dialog_durations.append((last_message_at - first_message_at).total_seconds())
        if isinstance(first_message_at, datetime) and isinstance(dialog_created_at, datetime):
            first_message_delays.append((first_message_at - dialog_created_at).total_seconds())

    summary = StatsSummary(
        dialogs={
            "total": total_dialogs or 0,
            "active": active_dialogs or 0,
            "by_status": dialog_status_breakdown,
        },
        timing={
            "average_dialog_duration_seconds": _calculate_average(dialog_durations),
            "average_time_to_first_message_seconds": _calculate_average(first_message_delays),
        },
    )
    return summary


@router.get("/admins", response_model=AdminsStatsResponse)
async def get_admins(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AdminsStatsResponse:
    bot = await session.scalar(
        select(Bot)
        .options(
            selectinload(Bot.account).selectinload(Account.owner),
            selectinload(Bot.account).selectinload(Account.operators),
        )
        .where(Bot.id == bot_id)
    )

    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    admins: list[AdminInfo] = []
    if bot.account and bot.account.owner:
        admins.append(
            AdminInfo(
                id=bot.account.owner.id,
                email=bot.account.owner.email,
                full_name=bot.account.owner.full_name,
            )
        )

    seen_ids = {admin.id for admin in admins}
    if bot.account and bot.account.operators:
        for operator in bot.account.operators:
            if operator.id in seen_ids:
                continue
            admins.append(
                AdminInfo(id=operator.id, email=operator.email, full_name=operator.full_name)
            )
            seen_ids.add(operator.id)

    return AdminsStatsResponse(admins=admins)
