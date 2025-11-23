"""Channel sender registry and base class definitions."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx
from sqlalchemy import select

from app.database import async_session_factory
from app.modules.channels.models import BotChannel, ChannelType
from app.modules.dialogs.models import Dialog
from app.modules.channels.service import ChannelsService

logger = logging.getLogger(__name__)


class BaseChannelSender(ABC):
    """Base contract for sending messages through a channel."""

    @abstractmethod
    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        """Send a text message to an external chat."""


_sender_registry: dict[ChannelType, type[BaseChannelSender]] = {}


def register_sender(channel_type: ChannelType, sender_cls: type[BaseChannelSender]) -> None:
    """Register a sender implementation for a given channel type."""

    _sender_registry[channel_type] = sender_cls


def get_sender(channel_type: ChannelType) -> type[BaseChannelSender]:
    """Retrieve a sender implementation for a given channel type."""

    return _sender_registry[channel_type]


class TelegramSender(BaseChannelSender):
    def __init__(self) -> None:
        self.channels_service = ChannelsService()

    async def _get_channel(self, bot_id: int) -> BotChannel | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BotChannel).where(
                    BotChannel.bot_id == bot_id,
                    BotChannel.channel_type == ChannelType.TELEGRAM,
                )
            )
            channel = result.scalars().first()
            if channel:
                channel = self.channels_service.decrypt(channel)
            return channel

    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        channel = await self._get_channel(bot_id)
        if not channel:
            logger.warning("No Telegram channel configured for bot", extra={"bot_id": bot_id})
            return

        token = channel.config.get("token") or channel.config.get("bot_token")
        if not token:
            logger.error(
                "Telegram channel config missing bot token",
                extra={"bot_id": bot_id, "channel_id": channel.id},
            )
            return

        payload = {"chat_id": external_chat_id, "text": text}
        url = f"https://api.telegram.org/bot{token}/sendMessage"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                if not data.get("ok", False):
                    logger.error(
                        "Telegram API returned unsuccessful response",
                        extra={
                            "bot_id": bot_id,
                            "channel_id": channel.id,
                            "status": response.status_code,
                            "response": data,
                        },
                    )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Telegram API responded with HTTP error",
                exc_info=exc,
                extra={
                    "bot_id": bot_id,
                    "channel_id": channel.id,
                    "status": exc.response.status_code if exc.response else None,
                },
            )
        except httpx.RequestError as exc:
            logger.error(
                "Failed to reach Telegram API",
                exc_info=exc,
                extra={"bot_id": bot_id, "channel_id": channel.id},
            )
        except Exception:  # pragma: no cover - safeguard for unexpected errors
            logger.exception(
                "Unexpected error while sending Telegram message",
                extra={"bot_id": bot_id, "channel_id": channel.id},
            )


class WhatsappGreenSender(BaseChannelSender):
    def __init__(self) -> None:
        self.channels_service = ChannelsService()

    async def _get_channel(self, bot_id: int) -> BotChannel | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BotChannel).where(
                    BotChannel.bot_id == bot_id,
                    BotChannel.channel_type == ChannelType.WHATSAPP_GREEN,
                )
            )
            channel = result.scalars().first()
            if channel:
                channel = self.channels_service.decrypt(channel)
            return channel

    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        channel = await self._get_channel(bot_id)
        if not channel:
            logger.warning(
                "No WhatsApp Green channel configured for bot",
                extra={"bot_id": bot_id, "chat_id": external_chat_id},
            )
            return

        if attachments:
            logger.info(
                "WhatsApp Green attachments are not supported yet; ignoring",
                extra={
                    "bot_id": bot_id,
                    "channel_id": channel.id,
                    "chat_id": external_chat_id,
                    "attachments_count": len(attachments),
                },
            )

        config = channel.config or {}
        send_message_url = config.get("send_message_url")
        if not send_message_url:
            api_base_url = config.get("api_base_url")
            send_message_path = config.get("send_message_path")
            instance_id = config.get("instance_id")
            api_token = config.get("api_token")

            if send_message_path and (instance_id or api_token):
                try:
                    send_message_path = send_message_path.format(
                        instance_id=instance_id or "", api_token=api_token or ""
                    )
                except Exception:  # pragma: no cover - defensive formatting guard
                    logger.exception(
                        "Failed to format WhatsApp Green send_message_path",
                        extra={
                            "bot_id": bot_id,
                            "channel_id": channel.id,
                            "chat_id": external_chat_id,
                        },
                    )

            if api_base_url and send_message_path:
                send_message_url = (
                    f"{api_base_url.rstrip('/')}/{send_message_path.lstrip('/')}"
                )

        if not send_message_url:
            logger.error(
                "WhatsApp Green channel config missing send message URL",
                extra={"bot_id": bot_id, "channel_id": channel.id, "chat_id": external_chat_id},
            )
            return

        payload = {"chatId": external_chat_id, "message": text}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(send_message_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "WhatsApp Green API responded with HTTP error",
                exc_info=exc,
                extra={
                    "bot_id": bot_id,
                    "channel_id": channel.id,
                    "chat_id": external_chat_id,
                    "status": exc.response.status_code if exc.response else None,
                    "response": exc.response.text if exc.response else None,
                },
            )
        except httpx.RequestError as exc:
            logger.error(
                "Failed to reach WhatsApp Green API",
                exc_info=exc,
                extra={
                    "bot_id": bot_id,
                    "channel_id": channel.id,
                    "chat_id": external_chat_id,
                },
            )
        except Exception:  # pragma: no cover - safeguard for unexpected errors
            logger.exception(
                "Unexpected error while sending WhatsApp Green message",
                extra={
                    "bot_id": bot_id,
                    "channel_id": channel.id,
                    "chat_id": external_chat_id,
                },
            )


class Whatsapp360Sender(BaseChannelSender):
    def __init__(self) -> None:
        self.channels_service = ChannelsService()

    async def _get_channel(self, bot_id: int) -> BotChannel | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BotChannel).where(
                    BotChannel.bot_id == bot_id,
                    BotChannel.channel_type == ChannelType.WHATSAPP_360,
                )
            )
            channel = result.scalars().first()
            if channel:
                channel = self.channels_service.decrypt(channel)
            return channel

    async def _resolve_user_id(self, bot_id: int, external_chat_id: str) -> str | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Dialog.external_user_id)
                .where(
                    Dialog.bot_id == bot_id,
                    Dialog.channel_type == ChannelType.WHATSAPP_360,
                    Dialog.external_chat_id == external_chat_id,
                )
                .order_by(Dialog.updated_at.desc())
            )
            return result.scalars().first()

    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        channel = await self._get_channel(bot_id)
        if not channel:
            logger.warning(
                "No WhatsApp 360 channel configured for bot",
                extra={"bot_id": bot_id, "chat_id": external_chat_id},
            )
            return

        if attachments:
            logger.info(
                "WhatsApp 360 attachments are not supported yet; ignoring",
                extra={
                    "bot_id": bot_id,
                    "channel_id": channel.id,
                    "chat_id": external_chat_id,
                    "attachments_count": len(attachments),
                },
            )

        config = channel.config or {}
        auth_token = config.get("auth_token") or config.get("token")
        send_message_url = config.get("send_message_url")
        if not send_message_url:
            api_base_url = config.get("api_base_url")
            send_message_path = config.get("send_message_path")
            if api_base_url and send_message_path:
                send_message_url = f"{api_base_url.rstrip('/')}/{send_message_path.lstrip('/')}"

        if not auth_token or not send_message_url:
            logger.error(
                "WhatsApp 360 channel config missing API url or token",
                extra={"bot_id": bot_id, "channel_id": channel.id},
            )
            return

        resolved_user_id = await self._resolve_user_id(bot_id, external_chat_id)
        to_value = resolved_user_id or external_chat_id

        payload = {"to": to_value, "type": "text", "text": {"body": text}}
        headers = {"Authorization": f"Bearer {auth_token}"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(send_message_url, json=payload, headers=headers)
                if not response.is_success:
                    logger.error(
                        "WhatsApp 360 API returned unsuccessful response",
                        extra={
                            "bot_id": bot_id,
                            "channel_id": channel.id,
                            "chat_id": external_chat_id,
                            "status": response.status_code,
                            "response": response.text,
                        },
                    )
        except httpx.HTTPError as exc:
            logger.error(
                "Failed to send WhatsApp 360 message",
                exc_info=exc,
                extra={"bot_id": bot_id, "channel_id": channel.id, "chat_id": external_chat_id},
            )


class WhatsappCustomSender(BaseChannelSender):
    def __init__(self) -> None:
        self.channels_service = ChannelsService()

    async def _get_channel(self, bot_id: int) -> BotChannel | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BotChannel).where(
                    BotChannel.bot_id == bot_id,
                    BotChannel.channel_type == ChannelType.WHATSAPP_CUSTOM,
                )
            )
            channel = result.scalars().first()
            if channel:
                channel = self.channels_service.decrypt(channel)
            return channel

    async def _resolve_user_id(self, bot_id: int, external_chat_id: str) -> str:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Dialog.external_user_id)
                .where(
                    Dialog.bot_id == bot_id,
                    Dialog.channel_type == ChannelType.WHATSAPP_CUSTOM,
                    Dialog.external_chat_id == external_chat_id,
                )
                .order_by(Dialog.updated_at.desc())
            )
            resolved_user_id = result.scalars().first()
            return resolved_user_id or external_chat_id

    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        channel = await self._get_channel(bot_id)
        if not channel:
            logger.warning(
                "No WhatsApp custom channel configured for bot",
                extra={"bot_id": bot_id, "chat_id": external_chat_id},
            )
            return

        config = channel.config or {}
        send_message_url = config.get("send_message_url")
        token = config.get("auth_token") or config.get("token")
        api_key_header = config.get("api_key_header")
        api_key = config.get("api_key")
        extra_headers = config.get("extra_headers") or {}

        if not send_message_url:
            logger.error(
                "WhatsApp custom channel config missing send_message_url",
                extra={"bot_id": bot_id, "channel_id": channel.id},
            )
            return

        external_user_id = await self._resolve_user_id(bot_id, external_chat_id)
        payload = {
            "chat_id": external_chat_id,
            "user_id": external_user_id,
            "text": text,
        }

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if api_key and api_key_header:
            headers[api_key_header] = api_key
        if isinstance(extra_headers, dict):
            headers.update(extra_headers)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    send_message_url, json=payload, headers=headers
                )
                if not response.is_success:
                    logger.error(
                        "WhatsApp custom API returned unsuccessful response",
                        extra={
                            "bot_id": bot_id,
                            "channel_id": channel.id,
                            "chat_id": external_chat_id,
                            "status": response.status_code,
                            "response": response.text,
                        },
                    )
        except httpx.HTTPError as exc:
            logger.error(
                "Failed to send WhatsApp custom message",
                exc_info=exc,
                extra={"bot_id": bot_id, "channel_id": channel.id, "chat_id": external_chat_id},
            )


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

    async def _resolve_user_id(self, bot_id: int, external_chat_id: str) -> str:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Dialog.external_user_id)
                    .where(
                        Dialog.bot_id == bot_id,
                        Dialog.channel_type == ChannelType.AVITO,
                        Dialog.external_chat_id == external_chat_id,
                    )
                    .order_by(Dialog.updated_at.desc())
            )
            existing_user_id = result.scalars().first()
            return existing_user_id or external_chat_id

    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        channel = await self._get_channel(bot_id)
        if not channel:
            logger.warning("No Avito channel configured for bot", extra={"bot_id": bot_id})
            return

        config = channel.config or {}
        token = config.get("auth_token") or config.get("token")
        send_message_url = config.get("send_message_url")
        if not send_message_url:
            api_base_url = config.get("api_base_url")
            send_message_path = config.get("send_message_path")
            if api_base_url and send_message_path:
                send_message_url = f"{api_base_url.rstrip('/')}/{send_message_path.lstrip('/')}"

        if not token or not send_message_url:
            logger.error(
                "Avito channel config missing API url or token",
                extra={"bot_id": bot_id, "channel_id": channel.id},
            )
            return

        resolved_user_id = await self._resolve_user_id(bot_id, external_chat_id)
        payload = {
            "chat_id": external_chat_id,
            "user_id": resolved_user_id,
            "message": {"text": text},
        }
        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(send_message_url, json=payload, headers=headers)
                if not response.is_success:
                    logger.error(
                        "Avito API returned unsuccessful response",
                        extra={
                            "bot_id": bot_id,
                            "channel_id": channel.id,
                            "status": response.status_code,
                            "response": response.text,
                        },
                    )
        except httpx.HTTPError as exc:
            logger.error(
                "Failed to send Avito message",
                exc_info=exc,
                extra={"bot_id": bot_id, "channel_id": channel.id},
            )


class MaxSender(BaseChannelSender):
    def __init__(self) -> None:
        self.channels_service = ChannelsService()

    async def _get_channel(self, bot_id: int) -> BotChannel | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BotChannel).where(
                    BotChannel.bot_id == bot_id,
                    BotChannel.channel_type == ChannelType.MAX,
                )
            )
            channel = result.scalars().first()
            if channel:
                channel = self.channels_service.decrypt(channel)
            return channel

    async def _resolve_user_id(self, bot_id: int, external_chat_id: str) -> str | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Dialog.external_user_id)
                .where(
                    Dialog.bot_id == bot_id,
                    Dialog.channel_type == ChannelType.MAX,
                    Dialog.external_chat_id == external_chat_id,
                )
                .order_by(Dialog.updated_at.desc())
            )
            return result.scalars().first()

    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        channel = await self._get_channel(bot_id)
        if not channel:
            logger.warning("No Max channel configured for bot", extra={"bot_id": bot_id})
            return

        config = channel.config or {}
        token = config.get("auth_token") or config.get("token")
        send_message_url = config.get("send_message_url")
        if not send_message_url:
            api_base_url = config.get("api_base_url")
            send_message_path = config.get("send_message_path")
            if api_base_url and send_message_path:
                send_message_url = f"{api_base_url.rstrip('/')}/{send_message_path.lstrip('/')}"

        if not token or not send_message_url:
            logger.error(
                "Max channel config missing API url or token",
                extra={"bot_id": bot_id, "channel_id": channel.id},
            )
            return

        resolved_user_id = await self._resolve_user_id(bot_id, external_chat_id)
        payload = {"chat_id": external_chat_id, "message": {"text": text}}
        if resolved_user_id:
            payload["user_id"] = resolved_user_id

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(send_message_url, json=payload, headers=headers)
                if not response.is_success:
                    logger.error(
                        "Max API returned unsuccessful response",
                        extra={
                            "bot_id": bot_id,
                            "channel_id": channel.id,
                            "chat_id": external_chat_id,
                            "status": response.status_code,
                            "response": response.text,
                        },
                    )
        except httpx.HTTPError as exc:
            logger.error(
                "Failed to send Max message",
                exc_info=exc,
                extra={"bot_id": bot_id, "channel_id": channel.id, "chat_id": external_chat_id},
            )


class WebchatSender(BaseChannelSender):
    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        logger.info(
            "Webchat sender is not configured; skipping send",
            extra={"bot_id": bot_id, "chat_id": external_chat_id},
        )


register_sender(ChannelType.TELEGRAM, TelegramSender)
register_sender(ChannelType.WHATSAPP_GREEN, WhatsappGreenSender)
register_sender(ChannelType.WHATSAPP_360, Whatsapp360Sender)
register_sender(ChannelType.WHATSAPP_CUSTOM, WhatsappCustomSender)
register_sender(ChannelType.AVITO, AvitoSender)
register_sender(ChannelType.MAX, MaxSender)
register_sender(ChannelType.WEBCHAT, WebchatSender)
