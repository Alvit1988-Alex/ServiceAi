"""Tests for Bitrix24 connector registration behavior."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[4]))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
os.environ.setdefault("JWT_SECRET_KEY", "test" * 8)
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "refresh" * 5)
os.environ.setdefault("CHANNEL_CONFIG_SECRET_KEY", "secret")

from app.modules.integrations.bitrix24.service import Bitrix24Service, BitrixIntegrationError


def test_ensure_connector_registered_is_idempotent(monkeypatch) -> None:
    service = Bitrix24Service()
    integration = SimpleNamespace(bot_id=7, portal_url="https://example.bitrix24.ru")
    call_count = {"value": 0}

    async def fake_call_rest(**_kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            return {"result": True}
        raise BitrixIntegrationError("ERROR_CONNECTOR_ALREADY_EXISTS: already registered")

    monkeypatch.setattr(service, "call_rest", fake_call_rest)

    async def run_check() -> tuple[bool, bool]:
        first = await service.ensure_connector_registered(session=None, integration=integration)
        second = await service.ensure_connector_registered(session=None, integration=integration)
        return first, second

    first, second = asyncio.run(run_check())
    assert first is True
    assert second is True
    assert call_count["value"] == 2
