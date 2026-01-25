"""Diagnostics execution service."""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.modules.accounts.models import User
from app.modules.bots.models import Bot
from app.modules.bots.service import BotsService
from app.modules.channels.models import ChannelType
from app.modules.channels.service import ChannelsService
from app.modules.diagnostics.models import IntegrationLog
from app.modules.diagnostics.schemas import DiagnosticCheck, DiagnosticsResponse, DiagnosticsSummary, IntegrationError
from app.utils.encryption import decrypt_config

logger = logging.getLogger(__name__)


async def log_integration_event(
    session: AsyncSession,
    *,
    account_id: int,
    channel_type: str,
    direction: str,
    operation: str,
    status: str,
    bot_id: int | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    latency_ms: int | None = None,
    external_id: str | None = None,
    request_id: str | None = None,
    retry_count: int = 0,
    http_status: int | None = None,
    endpoint: str | None = None,
    provider: str | None = None,
) -> None:
    """Persist an integration event without exposing sensitive payloads."""

    log_entry = IntegrationLog(
        account_id=account_id,
        bot_id=bot_id,
        channel_type=channel_type,
        direction=direction,
        operation=operation,
        status=status,
        error_code=error_code,
        error_message=error_message,
        latency_ms=latency_ms,
        external_id=external_id,
        request_id=request_id,
        retry_count=retry_count,
        http_status=http_status,
        endpoint=endpoint,
        provider=provider,
    )

    try:
        async with session.begin_nested():
            session.add(log_entry)
    except Exception:
        # Diagnostics should not crash on logging issues.
        return


class DiagnosticsService:
    REQUIRED_TABLES = {
        "users",
        "accounts",
        "bots",
        "dialogs",
        "dialog_messages",
        "bot_channels",
        "ai_instructions",
        "knowledge_files",
        "knowledge_chunks",
    }

    def __init__(self) -> None:
        self.bots_service = BotsService()
        self.channels_service = ChannelsService()

    async def log_integration(
        self,
        *,
        account_id: int | None,
        bot_id: int | None,
        channel_type: str,
        direction: str,
        operation: str,
        status: str,
        error_message: str | None = None,
        latency_ms: int | None = None,
        http_status: int | None = None,
        endpoint: str | None = None,
        provider: str | None = None,
        external_id: str | None = None,
        request_id: str | None = None,
        error_code: str | None = None,
        retry_count: int = 0,
    ) -> None:
        async with async_session_factory() as session:
            try:
                resolved_account_id = account_id
                if resolved_account_id is None and bot_id is not None:
                    result = await session.execute(select(Bot.account_id).where(Bot.id == bot_id))
                    resolved_account_id = result.scalar_one_or_none()
                if resolved_account_id is None:
                    resolved_account_id = 0

                await log_integration_event(
                    session,
                    account_id=resolved_account_id,
                    bot_id=bot_id,
                    channel_type=channel_type,
                    direction=direction,
                    operation=operation,
                    status=status,
                    error_code=error_code,
                    error_message=error_message,
                    latency_ms=latency_ms,
                    external_id=external_id,
                    request_id=request_id,
                    retry_count=retry_count,
                    http_status=http_status,
                    endpoint=endpoint,
                    provider=provider,
                )
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("Diagnostics integration logging failed")

    @staticmethod
    def parse_since(since: str | None) -> datetime | None:
        if not since:
            return None

        value = since.strip().lower()
        multiplier = 1
        if value.endswith("h"):
            multiplier = 3600
            value = value[:-1]
        elif value.endswith("d"):
            multiplier = 86400
            value = value[:-1]
        elif value.endswith("m"):
            multiplier = 60
            value = value[:-1]

        try:
            amount = float(value)
        except ValueError as exc:
            raise ValueError("Неверный формат параметра since") from exc

        seconds = amount * multiplier
        return datetime.now(timezone.utc) - timedelta(seconds=seconds)

    async def run(
        self,
        session: AsyncSession,
        *,
        mode: str,
        account_id: int | None = None,
        bot_id: int | None = None,
        since: str | None = None,
    ) -> DiagnosticsResponse:
        since_dt = self.parse_since(since)
        checks: list[DiagnosticCheck] = []

        checks.append(self._api_alive())
        checks.append(await self._db_select_one(session))
        checks.append(await self._db_schema_sanity(session))
        checks.append(await self._auth_sanity(session))

        bots: list[Bot] = []
        if mode in {"deep", "full"}:
            bots = await self._load_bots(session, account_id=account_id, bot_id=bot_id)
            checks.append(self._bots_list_check(bots, account_id=account_id, bot_id=bot_id))
            channel_checks = await self._channels_config_checks(session, bots)
            checks.extend(channel_checks)
            telegram_checks = await self._telegram_getme_checks(session, bots)
            checks.extend(telegram_checks)
            checks.append(self._webchat_placeholder())

        if mode == "full":
            checks.append(self._webhook_simulation_placeholder())

        summary = self._build_summary(checks)
        recent_errors = await self._load_recent_errors(
            session, since=since_dt, account_id=account_id, bot_id=bot_id
        )

        return DiagnosticsResponse(summary=summary, checks=checks, recent_errors=recent_errors)

    def _build_summary(self, checks: list[DiagnosticCheck]) -> DiagnosticsSummary:
        counters = {"ok": 0, "warn": 0, "fail": 0}
        for check in checks:
            counters[check.status] = counters.get(check.status, 0) + 1
        return DiagnosticsSummary(**counters)

    def _api_alive(self) -> DiagnosticCheck:
        return DiagnosticCheck(
            code="api_alive",
            title="API диагностики отвечает",
            status="ok",
            severity="fail",
        )

    async def _db_select_one(self, session: AsyncSession) -> DiagnosticCheck:
        start = time.perf_counter()
        try:
            await session.execute(text("SELECT 1"))
            latency_ms = math.floor((time.perf_counter() - start) * 1000)
            return DiagnosticCheck(
                code="db_select_1",
                title="Подключение к базе данных установлено",
                status="ok",
                severity="fail",
                details=f"latency={latency_ms}ms",
            )
        except Exception as exc:
            await log_integration_event(
                session,
                account_id=0,
                bot_id=None,
                channel_type="internal",
                direction="internal",
                operation="diagnostics_check",
                status="fail",
                error_message="Не удалось выполнить SELECT 1",
            )
            return DiagnosticCheck(
                code="db_select_1",
                title="Подключение к базе данных установлено",
                status="fail",
                severity="fail",
                details="Ошибка подключения к базе данных",
            )

    async def _db_schema_sanity(self, session: AsyncSession) -> DiagnosticCheck:
        result = await session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        tables = {row[0] for row in result.fetchall()}
        missing = sorted(self.REQUIRED_TABLES - tables)

        if missing:
            await log_integration_event(
                session,
                account_id=0,
                bot_id=None,
                channel_type="internal",
                direction="internal",
                operation="diagnostics_check",
                status="fail",
                error_message=f"Отсутствуют таблицы: {', '.join(missing)}",
            )
            return DiagnosticCheck(
                code="db_schema_sanity",
                title="Проверка целостности схемы БД",
                status="fail",
                severity="fail",
                details=f"Отсутствуют таблицы: {', '.join(missing)}",
            )

        return DiagnosticCheck(
            code="db_schema_sanity",
            title="Проверка целостности схемы БД",
            status="ok",
            severity="fail",
            details=f"found={len(tables)}",
        )

    async def _auth_sanity(self, session: AsyncSession) -> DiagnosticCheck:
        users_count = await session.scalar(select(func.count(User.id)))
        if not users_count:
            return DiagnosticCheck(
                code="auth_sanity",
                title="Проверка учетных данных",
                status="warn",
                severity="warn",
                details="Пропущено: нет тестовых учетных данных",
            )
        return DiagnosticCheck(
            code="auth_sanity",
            title="Проверка учетных данных",
            status="ok",
            severity="warn",
            details="Пользователи найдены",
        )

    async def _load_bots(
        self, session: AsyncSession, *, account_id: int | None, bot_id: int | None
    ) -> list[Bot]:
        filters: dict[str, Any] = {}
        if account_id is not None:
            filters["account_id"] = account_id
        if bot_id is not None:
            filters["id"] = bot_id
        return await self.bots_service.list(session=session, filters=filters or None)

    def _bots_list_check(
        self, bots: list[Bot], *, account_id: int | None, bot_id: int | None
    ) -> DiagnosticCheck:
        if not bots:
            scope = []
            if account_id is not None:
                scope.append(f"account_id={account_id}")
            if bot_id is not None:
                scope.append(f"bot_id={bot_id}")
            scope_text = ", ".join(scope) if scope else "не найдены"
            return DiagnosticCheck(
                code="bots_list",
                title="Проверка списка ботов",
                status="warn",
                severity="warn",
                details=f"Боты {scope_text}",
            )

        return DiagnosticCheck(
            code="bots_list",
            title="Проверка списка ботов",
            status="ok",
            severity="warn",
            details=f"bots_count={len(bots)}",
        )

    async def _channels_config_checks(self, session: AsyncSession, bots: list[Bot]) -> list[DiagnosticCheck]:
        checks: list[DiagnosticCheck] = []
        for bot in bots:
            channels = await self.channels_service.list(session=session, bot_id=bot.id)
            if not channels:
                checks.append(
                    DiagnosticCheck(
                        code="channels_config",
                        title="Проверка каналов",
                        status="fail",
                        severity="fail",
                        account_id=bot.account_id,
                        bot_id=bot.id,
                        details="Каналы не настроены",
                    )
                )
                await log_integration_event(
                    session,
                    account_id=bot.account_id,
                    bot_id=bot.id,
                    channel_type="internal",
                    direction="internal",
                    operation="diagnostics_check",
                    status="fail",
                    error_message="Отсутствуют записи каналов",
                )
                continue

            decryption_errors: list[int] = []
            inactive_count = 0
            for channel in channels:
                try:
                    decrypt_config(channel.config)
                except Exception:
                    decryption_errors.append(channel.id)
                if not channel.is_active:
                    inactive_count += 1

            if decryption_errors:
                checks.append(
                    DiagnosticCheck(
                        code="channels_config",
                        title="Проверка каналов",
                        status="fail",
                        severity="fail",
                        account_id=bot.account_id,
                        bot_id=bot.id,
                        details=f"Ошибки расшифровки: {len(decryption_errors)}",
                    )
                )
                await log_integration_event(
                    session,
                    account_id=bot.account_id,
                    bot_id=bot.id,
                    channel_type="internal",
                    direction="internal",
                    operation="diagnostics_check",
                    status="fail",
                    error_message="Не удалось расшифровать конфигурацию каналов",
                )
                continue

            status = "ok"
            details = "Все каналы активны"
            if inactive_count:
                status = "warn"
                details = f"Неактивные каналы: {inactive_count}"

            checks.append(
                DiagnosticCheck(
                    code="channels_config",
                    title="Проверка каналов",
                    status=status,
                    severity="warn",
                    account_id=bot.account_id,
                    bot_id=bot.id,
                    details=details,
                )
            )

        return checks

    async def _telegram_getme_checks(self, session: AsyncSession, bots: list[Bot]) -> list[DiagnosticCheck]:
        checks: list[DiagnosticCheck] = []
        async with httpx.AsyncClient(timeout=10) as client:
            for bot in bots:
                telegram_channels = [
                    ch
                    for ch in await self.channels_service.list(session=session, bot_id=bot.id)
                    if ch.channel_type == ChannelType.TELEGRAM
                ]
                if not telegram_channels:
                    continue

                for channel in telegram_channels:
                    try:
                        config = decrypt_config(channel.config) if channel.config else {}
                    except Exception:
                        checks.append(
                            DiagnosticCheck(
                                code="telegram_getme",
                                title="Telegram getMe",
                                status="fail",
                                severity="fail",
                                account_id=bot.account_id,
                                bot_id=bot.id,
                                details="Ошибка расшифровки конфигурации",
                            )
                        )
                        await log_integration_event(
                            session,
                            account_id=bot.account_id,
                            bot_id=bot.id,
                            channel_type="telegram",
                            direction="internal",
                            operation="diagnostics_check",
                            status="fail",
                            error_message="Ошибка расшифровки конфигурации Telegram",
                        )
                        continue

                    token = (config or {}).get("token")
                    if not token:
                        checks.append(
                            DiagnosticCheck(
                                code="telegram_getme",
                                title="Telegram getMe",
                                status="warn",
                                severity="warn",
                                account_id=bot.account_id,
                                bot_id=bot.id,
                                details="Токен не задан",
                            )
                        )
                        continue

                    api_url = f"https://api.telegram.org/bot{token}/getMe"
                    status_value = "ok"
                    details = "Токен задан"
                    http_status: int | None = None
                    try:
                        response = await client.get(api_url)
                        http_status = response.status_code
                        if response.status_code in (401, 403):
                            status_value = "fail"
                            details = "Телеграм вернул 401/403"
                        elif not response.is_success:
                            status_value = "warn"
                            details = f"Ответ Telegram: {response.status_code}"
                    except httpx.RequestError:
                        status_value = "warn"
                        details = "Ошибка запроса к Telegram"

                    checks.append(
                        DiagnosticCheck(
                            code="telegram_getme",
                            title="Telegram getMe",
                            status=status_value,
                            severity="fail",
                            account_id=bot.account_id,
                            bot_id=bot.id,
                            details=details,
                        )
                    )

                    if status_value == "fail":
                        await log_integration_event(
                            session,
                            account_id=bot.account_id,
                            bot_id=bot.id,
                            channel_type="telegram",
                            direction="out",
                            operation="telegram_getme",
                            status="fail",
                            http_status=http_status,
                            error_message="Telegram getMe вернул ошибку авторизации",
                            endpoint="getMe",
                        )

        return checks

    def _webchat_placeholder(self) -> DiagnosticCheck:
        return DiagnosticCheck(
            code="webchat_ws",
            title="Проверка WebSocket",
            status="warn",
            severity="warn",
            details="Проверка WebSocket пропущена",
        )

    def _webhook_simulation_placeholder(self) -> DiagnosticCheck:
        return DiagnosticCheck(
            code="webhook_simulation",
            title="Симуляция вебхуков",
            status="warn",
            severity="warn",
            details="Симуляция вебхуков пропущена",
        )

    async def _load_recent_errors(
        self,
        session: AsyncSession,
        *,
        since: datetime | None,
        account_id: int | None,
        bot_id: int | None,
    ) -> list[IntegrationError]:
        stmt = select(IntegrationLog).order_by(IntegrationLog.created_at.desc()).limit(50)
        if since:
            stmt = stmt.where(IntegrationLog.created_at >= since)
        if account_id is not None:
            stmt = stmt.where(IntegrationLog.account_id == account_id)
        if bot_id is not None:
            stmt = stmt.where(IntegrationLog.bot_id == bot_id)

        result = await session.execute(stmt)
        records: list[IntegrationLog] = result.scalars().all()
        return [
            IntegrationError(
                time=record.created_at,
                account_id=record.account_id,
                bot_id=record.bot_id,
                channel_type=record.channel_type,
                operation=record.operation,
                message=record.error_message or record.status,
            )
            for record in records
        ]


def get_diagnostics_service() -> DiagnosticsService:
    """Dependency injection helper for DiagnosticsService."""

    return DiagnosticsService()
