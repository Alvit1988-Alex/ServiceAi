"""Channel management CRUD operations and webhook helpers."""
from __future__ import annotations

import logging
import secrets
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.channels.avito_webhook import subscribe as avito_subscribe
from app.modules.channels.avito_webhook import unsubscribe as avito_unsubscribe
from app.modules.channels.models import BotChannel, ChannelType
from app.modules.channels.schemas import BotChannelCreate, BotChannelUpdate
from app.utils.encryption import decrypt_config, encrypt_config


logger = logging.getLogger(__name__)


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
        decrypted = self.decrypt(db_obj)

        await self._maybe_sync_avito_webhook(
            channel=decrypted,
            previous_active=False,
            previous_config=None,
        )

        return decrypted

    async def create_default_channels(
        self, session: AsyncSession, bot_id: int, channel_types: list[ChannelType] | None = None
    ) -> list[BotChannel]:
        """Create default active channels for a bot without committing the transaction."""

        default_types = channel_types or [
            ChannelType.TELEGRAM,
            ChannelType.WEBCHAT,
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
                is_active=True,
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
        previous_active = db_obj.is_active
        previous_config = decrypt_config(db_obj.config)
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
        decrypted = self.decrypt(db_obj)

        await self._maybe_sync_avito_webhook(
            channel=decrypted,
            previous_active=previous_active,
            previous_config=previous_config,
        )

        return decrypted

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

        if channel_type == ChannelType.AVITO:
            prepared.setdefault("client_id", "")
            prepared.setdefault("client_secret", "")
            prepared.setdefault("access_token", "")
            prepared.setdefault("refresh_token", "")
            prepared.setdefault("token_expires_at", "")
            prepared.setdefault("webhook_secret", "")
            prepared.setdefault("user_id", None)
            prepared.setdefault("reply_all_items", True)
            prepared.setdefault("allowed_item_ids", [])

        return prepared


    @staticmethod
    def should_reply_to_avito_message(config: dict[str, Any] | None, item_id: str | None) -> tuple[bool, str | None]:
        if not config:
            return True, None

        reply_all_raw = config.get("reply_all_items", True)
        reply_all = True
        if isinstance(reply_all_raw, str):
            reply_all = reply_all_raw.strip().lower() not in {"false", "0", "no", "off"}
        else:
            reply_all = bool(reply_all_raw)

        if reply_all:
            return True, None

        allowed = config.get("allowed_item_ids") or []
        normalized_item_id = str(item_id) if item_id is not None else None
        if not normalized_item_id:
            return False, "item_id_missing"

        allowed_as_str = {str(value) for value in allowed}
        if normalized_item_id in allowed_as_str:
            return True, None

        return False, "item_id_not_allowed"

    async def _maybe_sync_avito_webhook(
        self,
        channel: BotChannel,
        previous_active: bool,
        previous_config: dict[str, Any] | None,
    ) -> None:
        if channel.channel_type != ChannelType.AVITO:
            return

        base_url = settings.public_base_url
        if not base_url:
            logger.warning(
                "Public base URL is not configured; Avito webhook sync skipped",
                extra={"bot_id": channel.bot_id, "channel_id": channel.id},
            )
            return

        config = channel.config or {}
        webhook_secret = config.get("webhook_secret") or config.get("secret")
        if not webhook_secret and previous_config:
            webhook_secret = previous_config.get("webhook_secret") or previous_config.get("secret")

        if channel.is_active:
            required = [
                config.get("client_id"),
                config.get("client_secret"),
                config.get("user_id"),
                webhook_secret,
            ]
            if all(required):
                await avito_subscribe(channel, base_url)
            else:
                logger.warning(
                    "Avito webhook subscribe skipped due to missing config",
                    extra={
                        "bot_id": channel.bot_id,
                        "channel_id": channel.id,
                        "missing": [
                            key
                            for key, value in zip(
                                ["client_id", "client_secret", "user_id", "webhook_secret"],
                                required,
                            )
                            if not value
                        ],
                    },
                )
        elif previous_active and webhook_secret:
            await avito_unsubscribe(channel, base_url, webhook_secret=webhook_secret)


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
