"""Public webchat initialization endpoints."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.modules.accounts.models import Account, User
from app.modules.bots.models import Bot
from app.modules.channels.models import BotChannel, ChannelType

router = APIRouter(tags=["webchat"])


class WebchatInitIn(BaseModel):
    bot_id: int


class WebchatBotOut(BaseModel):
    id: int
    name: str


class WebchatConfigOut(BaseModel):
    name: str
    theme: str
    avatar_data_url: str | None
    avatar_url: str | None
    custom_colors_enabled: bool
    border_color: str | None
    button_color: str | None
    border_width: int


class WebchatInitOut(BaseModel):
    session_id: str
    ws_url: str
    bot: WebchatBotOut
    webchat_config: Optional[WebchatConfigOut] = None


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
        select(Bot, BotChannel, User.avatar_url)
        .join(BotChannel, BotChannel.bot_id == Bot.id)
        .join(Account, Account.id == Bot.account_id)
        .join(User, User.id == Account.owner_id)
        .where(
            Bot.id == payload.bot_id,
            BotChannel.channel_type == ChannelType.WEBCHAT,
            BotChannel.is_active.is_(True),
        )
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    bot, channel, avatar_url = row
    config = channel.config or {}
    config_theme = config.get("webchat_theme")
    theme = config_theme if config_theme in ("light", "dark", "neutral") else "light"
    border_width_raw = config.get("webchat_border_width")
    try:
        border_width = int(border_width_raw) if border_width_raw is not None else 1
    except (TypeError, ValueError):
        border_width = 1

    session_id = str(uuid.uuid4())
    ws_url = _resolve_ws_url(request, payload.bot_id, session_id)

    return WebchatInitOut(
        session_id=session_id,
        ws_url=ws_url,
        bot=WebchatBotOut(id=bot.id, name=bot.name),
        webchat_config=WebchatConfigOut(
            name=config.get("webchat_name") or bot.name,
            theme=theme,
            avatar_data_url=avatar_url,
            avatar_url=avatar_url,
            custom_colors_enabled=bool(config.get("webchat_custom_colors_enabled")),
            border_color=config.get("webchat_border_color"),
            button_color=config.get("webchat_button_color"),
            border_width=border_width,
        ),
    )
