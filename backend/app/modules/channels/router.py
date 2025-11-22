"""Channels router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.modules.accounts.models import User
from app.modules.channels.schemas import BotChannelCreate, BotChannelOut, BotChannelUpdate, ListResponse
from app.modules.channels.service import ChannelsService
from app.security.auth import get_current_user

router = APIRouter(prefix="/bots/{bot_id}/channels", tags=["channels"])


@router.post("", response_model=BotChannelOut, status_code=status.HTTP_201_CREATED)
async def create_channel(
    bot_id: int,
    data: BotChannelCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ChannelsService = Depends(ChannelsService),
) -> BotChannelOut:
    channel = await service.create(session=session, bot_id=bot_id, obj_in=data)
    return service.decrypt(channel)


@router.get("", response_model=ListResponse[BotChannelOut])
async def list_channels(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ChannelsService = Depends(ChannelsService),
) -> ListResponse[BotChannelOut]:
    items = service.decrypt_many(await service.list(session=session, bot_id=bot_id))
    return ListResponse[BotChannelOut](items=items)


@router.get("/{channel_id}", response_model=BotChannelOut)
async def get_channel(
    bot_id: int,
    channel_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ChannelsService = Depends(ChannelsService),
) -> BotChannelOut:
    channel = await service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return service.decrypt(channel)


@router.patch("/{channel_id}", response_model=BotChannelOut)
async def update_channel(
    bot_id: int,
    channel_id: int,
    data: BotChannelUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ChannelsService = Depends(ChannelsService),
) -> BotChannelOut:
    channel = await service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    updated = await service.update(session=session, db_obj=channel, obj_in=data)
    return service.decrypt(updated)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    bot_id: int,
    channel_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ChannelsService = Depends(ChannelsService),
) -> None:
    channel = await service.get(session=session, bot_id=bot_id, channel_id=channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    await service.delete(session=session, bot_id=bot_id, channel_id=channel_id)
