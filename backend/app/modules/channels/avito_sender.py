"""Sender implementation for Avito Messenger API."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy import select

from app.database import async_session_factory
from app.modules.channels.avito_auth import get_valid_access_token, request_access_token
from app.modules.channels.models import BotChannel, ChannelType
from app.modules.channels.sender_registry import BaseChannelSender
from app.modules.channels.service import ChannelsService

logger = logging.getLogger(__name__)
AVITO_SEND_MESSAGE_URL_TEMPLATE = "https://api.avito.ru/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages"


class AvitoSender(BaseChannelSender):
    def __init__(self) -> None:
        self.channels_service = ChannelsService()

    async def _get_channel(self, bot_id: int) -> BotChannel | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BotChannel).where(
                    BotChannel.bot_id == bot_id,
                    BotChannel.channel_type == ChannelType.AVITO,
                )
            )
            channel = result.scalars().first()
            if channel:
                channel = self.channels_service.decrypt(channel)
            return channel

    async def _send_request(self, url: str, payload: dict[str, Any], token: str) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            return await client.post(url, json=payload, headers=headers)

    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        channel = await self._get_channel(bot_id)
        if not channel:
            logger.warning("No Avito channel configured for bot", extra={"bot_id": bot_id})
            return

        if attachments:
            logger.info(
                "Avito attachments are not supported yet; ignoring",
                extra={
                    "bot_id": bot_id,
                    "channel_id": channel.id,
                    "conversation_id": external_chat_id,
                    "attachments_count": len(attachments),
                },
            )

        access_token = await get_valid_access_token(channel)
        if not access_token:
            logger.error(
                "Avito access token is not available",
                extra={"bot_id": bot_id, "channel_id": channel.id},
            )
            return

        user_id = channel.config.get("user_id")
        if not user_id:
            logger.error(
                "Avito config missing user_id",
                extra={"bot_id": bot_id, "channel_id": channel.id},
            )
            return

        url = AVITO_SEND_MESSAGE_URL_TEMPLATE.format(user_id=user_id, chat_id=external_chat_id)
        payload = {"message": {"text": text}, "type": "text"}

        try:
            response = await self._send_request(url, payload, access_token)
            if response.status_code in (401, 403):
                refreshed_token = await request_access_token(channel)
                if refreshed_token:
                    response = await self._send_request(url, payload, refreshed_token)

            if response.is_success:
                logger.info(
                    "Avito message sent",
                    extra={
                        "bot_id": bot_id,
                        "channel_id": channel.id,
                        "conversation_id": external_chat_id,
                        "status": response.status_code,
                    },
                )
                return

            logger.error(
                "Avito API returned unsuccessful response",
                extra={
                    "bot_id": bot_id,
                    "channel_id": channel.id,
                    "conversation_id": external_chat_id,
                    "status": response.status_code,
                    "response": response.text,
                },
            )
        except httpx.HTTPError as exc:
            logger.error(
                "Failed to send Avito message",
                exc_info=exc,
                extra={"bot_id": bot_id, "channel_id": channel.id, "conversation_id": external_chat_id},
            )
        except Exception:
            logger.exception(
                "Unexpected error while sending Avito message",
                extra={"bot_id": bot_id, "channel_id": channel.id, "conversation_id": external_chat_id},
            )
