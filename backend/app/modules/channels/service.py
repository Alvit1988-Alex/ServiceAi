"""Channel management CRUD operations and webhook helpers."""
from __future__ import annotations

import secrets
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.channels.models import BotChannel, ChannelType
from app.modules.channels.schemas import BotChannelCreate, BotChannelUpdate
from app.utils.encryption import decrypt_config, encrypt_config


class ChannelsService:
    model = BotChannel

    async def create(self, session: AsyncSession, bot_id: int, obj_in: BotChannelCreate) -> BotChannel:
        prepared_config = self._prepare_config(obj_in.channel_type, obj_in.config)
        db_obj = BotChannel(
            bot_id=bot_id,
            channel_type=obj_in.channel_type,
            config=encrypt_config(prepared_config),
            is_active=obj_in.is_active,
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return self.decrypt(db_obj)

    async def create_default_channels(
        self, session: AsyncSession, bot_id: int, channel_types: list[ChannelType] | None = None
    ) -> list[BotChannel]:
        """Create default inactive channels for a bot without committing the transaction."""

        default_types = channel_types or [
            ChannelType.TELEGRAM,
            ChannelType.WEBCHAT,
            ChannelType.WHATSAPP_GREEN,
            ChannelType.WHATSAPP_360,
            ChannelType.WHATSAPP_CUSTOM,
            ChannelType.AVITO,
            ChannelType.MAX,
        ]
        channels: list[BotChannel] = []

        for channel_type in default_types:
            prepared_config = self._prepare_config(channel_type, {})
            channel = BotChannel(
                bot_id=bot_id,
                channel_type=channel_type,
                config=encrypt_config(prepared_config),
                is_active=False,
            )
            session.add(channel)
            channels.append(channel)

        await session.flush()
        return channels

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
            prepared_config = self._prepare_config(db_obj.channel_type, data["config"])
            data["config"] = encrypt_config(prepared_config)
        elif db_obj.channel_type == ChannelType.TELEGRAM:
            current_config = decrypt_config(db_obj.config)
            prepared_config = self._prepare_config(db_obj.channel_type, current_config)
            if prepared_config != current_config:
                data["config"] = encrypt_config(prepared_config)
        for field, value in data.items():
            setattr(db_obj, field, value)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return self.decrypt(db_obj)

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

    def _prepare_config(self, channel_type: ChannelType, config: dict[str, Any] | None) -> dict[str, Any]:
        prepared = dict(config or {})

        if channel_type == ChannelType.TELEGRAM and not prepared.get("secret_token"):
            prepared["secret_token"] = secrets.token_hex(16)

        return prepared


async def sync_telegram_webhook(channel: BotChannel) -> tuple[str | None, str | None]:
    config = channel.config or {}
    token = config.get("token")
    secret_token = config.get("secret_token")

    if not token:
        return "pending", "Telegram token is not configured"

    base_url = settings.public_base_url
    if channel.is_active and not base_url:
        return "pending", "Public base URL is not configured"

    webhook_url = None
    if channel.is_active:
        webhook_url = f"{base_url.rstrip('/')}/bots/{channel.bot_id}/channels/webhooks/telegram/{channel.id}"

    api_url = f"https://api.telegram.org/bot{token}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if webhook_url:
                response = await client.post(
                    f"{api_url}/setWebhook",
                    params={"url": webhook_url, "secret_token": secret_token},
                )
            else:
                response = await client.post(f"{api_url}/deleteWebhook")

            response.raise_for_status()
            payload = response.json()
            if payload.get("ok"):
                return "ok", None
            return "error", str(payload.get("description")) if payload.get("description") else "Telegram API returned an error"
    except httpx.HTTPStatusError as exc:
        return "error", f"Telegram API error: {exc.response.status_code}"
    except httpx.RequestError as exc:
        return "error", f"Telegram request failed: {exc}"
