"""Channel sender registry and base class definitions."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.channels.models import ChannelType


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
    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        raise NotImplementedError


class WhatsappGreenSender(BaseChannelSender):
    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        raise NotImplementedError


class Whatsapp360Sender(BaseChannelSender):
    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        raise NotImplementedError


class WhatsappCustomSender(BaseChannelSender):
    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        raise NotImplementedError


class AvitoSender(BaseChannelSender):
    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        raise NotImplementedError


class MaxSender(BaseChannelSender):
    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        raise NotImplementedError


class WebchatSender(BaseChannelSender):
    async def send_text(
        self, bot_id: int, external_chat_id: str, text: str, attachments=None
    ) -> None:
        raise NotImplementedError


register_sender(ChannelType.TELEGRAM, TelegramSender)
register_sender(ChannelType.WHATSAPP_GREEN, WhatsappGreenSender)
register_sender(ChannelType.WHATSAPP_360, Whatsapp360Sender)
register_sender(ChannelType.WHATSAPP_CUSTOM, WhatsappCustomSender)
register_sender(ChannelType.AVITO, AvitoSender)
register_sender(ChannelType.MAX, MaxSender)
register_sender(ChannelType.WEBCHAT, WebchatSender)
