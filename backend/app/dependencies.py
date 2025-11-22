from typing import AsyncGenerator

from fastapi import Depends

from app import database
from app.modules.ai.service import AIService
from app.modules.channels.service import ChannelsService, ChannelSenderRegistry
from app.modules.dialogs.service import DialogService
from app.modules.dialogs.websocket_manager import WebSocketManager


async def get_db() -> AsyncGenerator[database.AsyncSession, None]:
    session = database.get_session()
    try:
        yield session
    finally:
        await session.close()


def get_channels_service() -> ChannelsService:
    return ChannelsService()


def get_ws_manager() -> WebSocketManager:
    return WebSocketManager()


def get_channel_sender_registry(
    channels_service: ChannelsService = Depends(get_channels_service),
    ws_manager: WebSocketManager = Depends(get_ws_manager),
) -> ChannelSenderRegistry:
    return ChannelSenderRegistry(channels_service=channels_service, websocket_manager=ws_manager)


def get_ai_service() -> AIService:
    return AIService()


def get_dialog_service(
    ai_service: AIService = Depends(get_ai_service),
    channel_sender_registry: ChannelSenderRegistry = Depends(get_channel_sender_registry),
) -> DialogService:
    return DialogService(ai_service=ai_service, channel_sender_registry=channel_sender_registry)
