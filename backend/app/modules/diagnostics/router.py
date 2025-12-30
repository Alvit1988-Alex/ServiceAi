"""Diagnostics API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db_session
from app.modules.diagnostics.schemas import DiagnosticsResponse
from app.modules.diagnostics.service import DiagnosticsService


router = APIRouter(prefix="", tags=["diagnostics"])


async def _verify_internal_key(
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    x_internal_api_key: str | None = Header(default=None, alias="X-Internal-Api-Key"),
) -> None:
    provided_key = x_internal_api_key or x_internal_key
    if not provided_key or provided_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get("/diagnostics", response_model=DiagnosticsResponse)
async def diagnostics_endpoint(
    mode: str = Query(default="fast", pattern="^(fast|deep|full)$"),
    account_id: int | None = Query(default=None),
    bot_id: int | None = Query(default=None),
    since: str | None = Query(default=None),
    _: None = Depends(_verify_internal_key),
    session: AsyncSession = Depends(get_db_session),
) -> DiagnosticsResponse:
    service = DiagnosticsService()
    try:
        return await service.run(
            session,
            mode=mode,
            account_id=account_id,
            bot_id=bot_id,
            since=since,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
