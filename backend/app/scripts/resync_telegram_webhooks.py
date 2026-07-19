"""CLI command to resynchronize active Telegram channel webhooks."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.modules.channels.models import BotChannel, ChannelType
from app.modules.channels.service import ChannelsService, sync_telegram_webhook


@dataclass(frozen=True)
class TelegramWebhookResyncResult:
    found: int
    updated: int
    failed: int


async def resync_active_telegram_webhooks(
    *,
    session: AsyncSession | None = None,
    sync_func: Callable[[BotChannel], Awaitable[tuple[str | None, str | None]]] = sync_telegram_webhook,
) -> TelegramWebhookResyncResult:
    """Resynchronize webhooks for all active Telegram channels once."""

    owns_session = session is None
    if session is None:
        session = async_session_factory()

    try:
        result = await session.execute(
            select(BotChannel).where(
                BotChannel.channel_type == ChannelType.TELEGRAM,
                BotChannel.is_active.is_(True),
            )
        )
        channels = list(result.scalars().all())
        service = ChannelsService()
        updated = 0
        failed = 0

        for channel in channels:
            try:
                decrypted = service.decrypt(channel)
                status, error = await sync_func(decrypted)
            except Exception as exc:  # noqa: BLE001 - continue resyncing remaining channels
                failed += 1
                print(f"Telegram webhook resync failed for channel_id={channel.id}: {type(exc).__name__}")
                continue

            if status == "ok" and not error:
                updated += 1
            else:
                failed += 1
                print(f"Telegram webhook resync failed for channel_id={channel.id}: {status or 'unknown'}")

        return TelegramWebhookResyncResult(
            found=len(channels),
            updated=updated,
            failed=failed,
        )
    finally:
        if owns_session:
            await session.close()


async def _async_main() -> TelegramWebhookResyncResult:
    result = await resync_active_telegram_webhooks()
    print(f"Telegram channels found: {result.found}")
    print(f"Telegram webhooks updated: {result.updated}")
    print(f"Telegram webhook errors: {result.failed}")
    return result


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
