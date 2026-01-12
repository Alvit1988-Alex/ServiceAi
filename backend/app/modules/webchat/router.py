"""Public webchat initialization endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.modules.bots.models import Bot
from app.modules.channels.models import BotChannel, ChannelType

router = APIRouter(tags=["webchat"])


class WebchatInitIn(BaseModel):
    bot_id: int


class WebchatBotOut(BaseModel):
    id: int
    name: str


class WebchatInitOut(BaseModel):
    session_id: str
    ws_url: str
    bot: WebchatBotOut


def _resolve_ws_url(request: Request, bot_id: int, session_id: str) -> str:
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    ws_scheme = "wss" if scheme == "https" else "ws"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{ws_scheme}://{host}/ws/webchat/{bot_id}/{session_id}"


@router.post("/webchat/init", response_model=WebchatInitOut)
async def init_webchat(
    payload: WebchatInitIn,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> WebchatInitOut:
    stmt = (
        select(Bot)
        .join(BotChannel, BotChannel.bot_id == Bot.id)
        .where(
            Bot.id == payload.bot_id,
            BotChannel.channel_type == ChannelType.WEBCHAT,
        )
    )
    result = await session.execute(stmt)
    bot = result.scalars().first()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    session_id = str(uuid.uuid4())
    ws_url = _resolve_ws_url(request, payload.bot_id, session_id)

    return WebchatInitOut(
        session_id=session_id,
        ws_url=ws_url,
        bot=WebchatBotOut(id=bot.id, name=bot.name),
    )
