from __future__ import annotations

import pytest

from app.modules.channels.models import BotChannel, ChannelType
from app.scripts.resync_telegram_webhooks import resync_active_telegram_webhooks


class FakeScalarResult:
    def __init__(self, channels: list[BotChannel]) -> None:
        self._channels = channels

    def all(self) -> list[BotChannel]:
        return self._channels


class FakeExecuteResult:
    def __init__(self, channels: list[BotChannel]) -> None:
        self._channels = channels

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._channels)


class FakeSession:
    def __init__(self, channels: list[BotChannel]) -> None:
        self.channels = channels

    async def execute(self, statement: object) -> FakeExecuteResult:
        return FakeExecuteResult(self.channels)


def _telegram_channel(channel_id: int, config: object | None = None) -> BotChannel:
    return BotChannel(
        id=channel_id,
        bot_id=channel_id + 100,
        channel_type=ChannelType.TELEGRAM,
        is_active=True,
        config=config or {"token": f"TOKEN-{channel_id}", "secret_token": "secret"},
    )


@pytest.mark.asyncio
async def test_resync_telegram_webhooks_calls_sync_for_each_channel() -> None:
    channels = [_telegram_channel(1), _telegram_channel(2)]
    synced: list[int] = []

    async def fake_sync(channel: BotChannel) -> tuple[str | None, str | None]:
        synced.append(channel.id)
        return "ok", None

    result = await resync_active_telegram_webhooks(
        session=FakeSession(channels),
        sync_func=fake_sync,
    )

    assert result.found == 2
    assert result.updated == 2
    assert result.failed == 0
    assert synced == [1, 2]


@pytest.mark.asyncio
async def test_resync_telegram_webhooks_continues_after_channel_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = [
        _telegram_channel(1, config="encrypted-1"),
        _telegram_channel(2, config="encrypted-2"),
        _telegram_channel(3, config="encrypted-3"),
    ]
    original_configs = [channel.config for channel in channels]
    synced: list[int] = []

    def fake_decrypt_config(config: object) -> dict[str, str]:
        return {"token": str(config), "secret_token": "secret"}

    monkeypatch.setattr(
        "app.scripts.resync_telegram_webhooks.decrypt_config", fake_decrypt_config
    )

    async def fake_sync(channel: BotChannel) -> tuple[str | None, str | None]:
        synced.append(channel.id)
        if channel.id == 2:
            raise RuntimeError("telegram unavailable")
        return "ok", None

    result = await resync_active_telegram_webhooks(
        session=FakeSession(channels),
        sync_func=fake_sync,
    )

    assert result.found == 3
    assert result.updated == 2
    assert result.failed == 1
    assert synced == [1, 2, 3]
    assert [channel.config for channel in channels] == original_configs

    synced.clear()
    second_result = await resync_active_telegram_webhooks(
        session=FakeSession(channels),
        sync_func=fake_sync,
    )

    assert second_result.found == 3
    assert second_result.updated == 2
    assert second_result.failed == 1
    assert synced == [1, 2, 3]
    assert [channel.config for channel in channels] == original_configs
