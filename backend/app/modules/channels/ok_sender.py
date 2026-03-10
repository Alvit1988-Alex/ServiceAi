"""Sender implementation for Odnoklassniki Bot API."""
from __future__ import annotations

import logging

import httpx
from sqlalchemy import select

from app.database import async_session_factory
from app.modules.channels.models import BotChannel, ChannelType
from app.modules.channels.sender_registry import BaseChannelSender
from app.modules.channels.service import ChannelsService

logger = logging.getLogger(__name__)


class OkSender(BaseChannelSender):
    def __init__(self) -> None:
        self.channels_service = ChannelsService()

    async def _get_channel(self, bot_id: int) -> BotChannel | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BotChannel)
                .where(
                    BotChannel.bot_id == bot_id,
                    BotChannel.channel_type == ChannelType.OK,
                )
                .order_by(BotChannel.is_active.desc(), BotChannel.id)
            )
            channel = result.scalars().first()
            if channel:
                channel = self.channels_service.decrypt(channel)
            return channel

    async def send_text(self, bot_id: int, external_chat_id: str, text: str, attachments=None) -> None:
        channel = await self._get_channel(bot_id)
        if not channel:
            logger.info("No OK channel configured for bot", extra={"bot_id": bot_id})
            return

        if not channel.is_active:
            logger.info("OK channel is inactive; skipping send", extra={"bot_id": bot_id, "channel_id": channel.id})
            return

        if attachments:
            logger.warning(
                "OK attachments are not supported yet; ignoring",
                extra={
                    "bot_id": bot_id,
                    "channel_id": channel.id,
                    "chat_id": external_chat_id,
                    "attachments_count": len(attachments),
                },
            )

        access_token = (channel.config or {}).get("access_token")
        if not access_token:
            logger.error("OK channel config missing access token", extra={"bot_id": bot_id, "channel_id": channel.id})
            return

        url = f"https://api.ok.ru/graph/{external_chat_id}/messages"
        params = {"access_token": access_token}
        json_body = {
            "recipient": {"chat_id": external_chat_id},
            "message": {"text": text},
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, params=params, json=json_body)

            if response.status_code != 200:
                logger.error(
                    "OK API responded with HTTP error",
                    extra={"bot_id": bot_id, "channel_id": channel.id, "status": response.status_code},
                )
        except httpx.HTTPError as exc:
            logger.error(
                "Failed to send OK message",
                exc_info=exc,
                extra={"bot_id": bot_id, "channel_id": channel.id, "chat_id": external_chat_id},
            )
