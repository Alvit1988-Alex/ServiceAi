"""Channel management CRUD operations."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.channels.models import BotChannel, ChannelType
from app.modules.channels.schemas import BotChannelCreate, BotChannelUpdate
from app.utils.encryption import decrypt_config, encrypt_config


class ChannelsService:
    model = BotChannel

    async def create(self, session: AsyncSession, bot_id: int, obj_in: BotChannelCreate) -> BotChannel:
        db_obj = BotChannel(
            bot_id=bot_id,
            channel_type=obj_in.channel_type,
            config=encrypt_config(obj_in.config),
            is_active=obj_in.is_active,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get(self, session: AsyncSession, bot_id: int, channel_id: int) -> BotChannel | None:
        stmt = select(BotChannel).where(BotChannel.id == channel_id, BotChannel.bot_id == bot_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def list(self, session: AsyncSession, bot_id: int) -> list[BotChannel]:
        result = await session.execute(select(BotChannel).where(BotChannel.bot_id == bot_id))
        return result.scalars().all()

    async def update(
        self,
        session: AsyncSession,
        db_obj: BotChannel,
        obj_in: BotChannelUpdate,
    ) -> BotChannel:
        data = obj_in.model_dump(exclude_unset=True)
        if "config" in data:
            data["config"] = encrypt_config(data["config"])
        for field, value in data.items():
            setattr(db_obj, field, value)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, session: AsyncSession, bot_id: int, channel_id: int) -> None:
        obj = await self.get(session, bot_id, channel_id)
        if obj:
            await session.delete(obj)
            await session.commit()

    def decrypt(self, channel: BotChannel) -> BotChannel:
        channel.config = decrypt_config(channel.config)
        return channel

    def decrypt_many(self, channels: list[BotChannel]) -> list[BotChannel]:
        return [self.decrypt(ch) for ch in channels]
