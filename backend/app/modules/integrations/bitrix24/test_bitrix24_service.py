"""Tests for Bitrix24 connector registration behavior."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import app.modules.integrations.bitrix24.service as bitrix_service_module
from app.modules.integrations.bitrix24.service import Bitrix24Service, BitrixIntegrationError


def test_ensure_connector_registered_is_idempotent(monkeypatch) -> None:
    service = Bitrix24Service()
    integration = SimpleNamespace(bot_id=7, portal_url="https://example.bitrix24.ru")
    call_count = {"value": 0}

    monkeypatch.setattr(bitrix_service_module.settings, "public_base_url", "https://example.com", raising=False)

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
