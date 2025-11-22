"""Channels router stub."""

from fastapi import APIRouter

from app.modules.channels.schemas import BotChannelConfigIn, BotChannelOut, ChannelType
from app.modules.channels.service import ChannelsService

router = APIRouter(prefix="/bots/{bot_id}/channels", tags=["channels"])


@router.get("", response_model=list[BotChannelOut])
async def list_channels(bot_id: int, service: ChannelsService = ChannelsService()):
    return await service.list_channels(bot_id)


@router.put("/{channel_type}", response_model=dict)
async def upsert_channel(bot_id: int, channel_type: ChannelType, data: BotChannelConfigIn, service: ChannelsService = ChannelsService()):
    return await service.upsert_channel_config(bot_id=bot_id, channel_type=channel_type, config=data.config)
