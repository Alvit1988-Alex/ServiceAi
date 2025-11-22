"""Channel management and sender registry stubs."""

from typing import Protocol

from app.modules.channels.schemas import ChannelType, NormalizedMessage


class ChannelsService:
    """CRUD operations for bot channels (placeholder)."""

    async def list_channels(self, bot_id: int) -> list:
        return []

    async def get_channel_by_type(self, bot_id: int, channel_type: ChannelType):
        return None

    async def upsert_channel_config(self, bot_id: int, channel_type: ChannelType, config: dict):
        return {"bot_id": bot_id, "type": channel_type, "config": config}

    async def enable_channel(self, bot_id: int, channel_type: ChannelType) -> None:
        return None

    async def disable_channel(self, bot_id: int, channel_type: ChannelType) -> None:
        return None

    async def get_decrypted_config(self, channel) -> dict:
        return {}


class ChannelSender(Protocol):
    async def send_message(self, bot_id: int, external_chat_id: str, text: str, attachments=None) -> None: ...


class ChannelSenderRegistry:
    def __init__(self, channels_service: ChannelsService, websocket_manager):
        self._channels_service = channels_service
        self._ws = websocket_manager
        self._map: dict[ChannelType, ChannelSender] = {}

    def register_sender(self, channel_type: ChannelType, sender: ChannelSender) -> None:
        self._map[channel_type] = sender

    def get_sender(self, channel_type: ChannelType) -> ChannelSender:
        return self._map[channel_type]
