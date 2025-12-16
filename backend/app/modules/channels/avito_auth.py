"""OAuth helpers for Avito API."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.database import async_session_factory
from app.modules.channels.models import BotChannel
from app.modules.channels.schemas import BotChannelUpdate
from app.modules.channels.service import ChannelsService

logger = logging.getLogger(__name__)

AVITO_TOKEN_REFRESH_URL = "https://api.avito.ru/token/refresh"
TOKEN_REFRESH_MARGIN_SECONDS = 30


def _parse_expires_at(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


async def get_valid_access_token(channel: BotChannel) -> str | None:
    config = channel.config or {}
    access_token = config.get("access_token")
    expires_at = _parse_expires_at(config.get("token_expires_at"))

    now = datetime.now(tz=timezone.utc)
    if access_token and expires_at and expires_at > now + timedelta(seconds=TOKEN_REFRESH_MARGIN_SECONDS):
        return access_token

    return await refresh_access_token(channel)


async def refresh_access_token(channel: BotChannel) -> str | None:
    config = channel.config or {}
    refresh_token = config.get("refresh_token")
    client_id = config.get("client_id")
    client_secret = config.get("client_secret")

    if not refresh_token or not client_id or not client_secret:
        logger.error(
            "Avito OAuth configuration incomplete for refresh",
            extra={"bot_id": channel.bot_id, "channel_id": channel.id},
        )
        return None

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(AVITO_TOKEN_REFRESH_URL, data=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Avito OAuth refresh failed with HTTP error",
            exc_info=exc,
            extra={
                "bot_id": channel.bot_id,
                "channel_id": channel.id,
                "status": exc.response.status_code if exc.response else None,
                "response": exc.response.text if exc.response else None,
            },
        )
        return None
    except httpx.RequestError as exc:
        logger.error(
            "Avito OAuth refresh request failed",
            exc_info=exc,
            extra={"bot_id": channel.bot_id, "channel_id": channel.id},
        )
        return None
    except Exception:
        logger.exception(
            "Unexpected error during Avito OAuth refresh",
            extra={"bot_id": channel.bot_id, "channel_id": channel.id},
        )
        return None

    access_token = data.get("access_token")
    new_refresh_token = data.get("refresh_token") or refresh_token
    expires_in = data.get("expires_in")

    expires_at: datetime | None = None
    if isinstance(expires_in, (int, float)):
        expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=int(expires_in))

    updated_config = dict(config)
    if access_token:
        updated_config["access_token"] = access_token
    updated_config["refresh_token"] = new_refresh_token
    if expires_at:
        updated_config["token_expires_at"] = expires_at.isoformat()

    channels_service = ChannelsService()
    async with async_session_factory() as session:
        db_channel = await channels_service.get(
            session=session, bot_id=channel.bot_id, channel_id=channel.id
        )
        if not db_channel:
            logger.error(
                "Avito channel not found during token refresh",
                extra={"bot_id": channel.bot_id, "channel_id": channel.id},
            )
            return access_token

        await channels_service.update(
            session=session,
            db_obj=db_channel,
            obj_in=BotChannelUpdate(config=updated_config),
        )

    logger.info(
        "Avito OAuth token refreshed successfully",
        extra={"bot_id": channel.bot_id, "channel_id": channel.id},
    )
    return access_token
