"""Command line client for diagnostics endpoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx


def _print_check(check: dict[str, Any], verbose: bool = False) -> None:
    status = check.get("status", "warn")
    prefix = {
        "ok": "[ OK ]",
        "warn": "[WARN]",
        "fail": "[FAIL]",
    }.get(status, "[WARN]")

    title = check.get("title", check.get("code", ""))
    print(f"{prefix} {title}")
    if verbose and check.get("details"):
        print(f"       детали: {check['details']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Запуск диагностики ServiceAI")
    parser.add_argument("--base-url", required=True, help="Базовый URL API, например http://localhost:8000")
    parser.add_argument("--mode", choices=["fast", "deep", "full"], default="fast")
    parser.add_argument("--account-id", type=int, dest="account_id")
    parser.add_argument("--bot-id", type=int, dest="bot_id")
    parser.add_argument("--since", help="Ограничение по времени (например, 24h, 7d, 60m)")
    parser.add_argument("--internal-key", help="INTERNAL_API_KEY, если не задан в окружении")
    parser.add_argument("--verbose", action="store_true", help="Показывать детали проверок")
    return parser.parse_args()


def main() -> int:
    if os.name == "nt":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    args = parse_args()
    internal_key = args.internal_key or os.getenv("INTERNAL_API_KEY")
    if not internal_key:
        print("[FAIL] Не указан INTERNAL_API_KEY", file=sys.stderr)
        return 2

    params = {"mode": args.mode}
    if args.account_id is not None:
        params["account_id"] = args.account_id
    if args.bot_id is not None:
        params["bot_id"] = args.bot_id
    if args.since:
        params["since"] = args.since

    url = f"{args.base_url.rstrip('/')}/diagnostics"
    try:
        response = httpx.get(
            url,
            params=params,
            headers={
                "X-Internal-Api-Key": internal_key,
                "X-Internal-Key": internal_key,
            },
            timeout=15.0,
        )
    except httpx.TimeoutException:
        print("[FAIL] Ошибка запроса: таймаут", file=sys.stderr)
        return 2
    except httpx.RequestError as exc:
        print(f"[FAIL] Ошибка запроса: {exc}", file=sys.stderr)
        return 2

    status_code = str(response.status_code)
    body = response.text.strip()

    if status_code == "403":
        print("[FAIL] Доступ запрещен (проверьте INTERNAL_API_KEY)")
        return 2
    if status_code != "200":
        print(f"[FAIL] Ошибка API: HTTP {status_code}")
        return 2

    if not body:
        print("[FAIL] Некорректный ответ от API")
        return 2

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        print("[FAIL] Некорректный ответ от API")
        return 2

    checks = payload.get("checks", [])
    for check in checks:
        _print_check(check, verbose=args.verbose)

    summary = payload.get("summary", {})
    ok = summary.get("ok", 0)
    warn = summary.get("warn", 0)
    fail = summary.get("fail", 0)
    print(f"ИТОГО: Успешно: {ok}, Предупреждения: {warn}, Ошибки: {fail}")

    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
