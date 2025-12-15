"""Command line client for diagnostics endpoint."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any
from urllib.parse import urlencode


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
    query = urlencode(params)
    status_marker = "__HTTP_STATUS__:"

    command = [
        "curl",
        "-sS",
        "-m",
        "15",
        "-H",
        f"X-Internal-Key: {internal_key}",
        f"{url}?{query}",
        "-w",
        "\n__HTTP_STATUS__:%{http_code}\n",
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        error_output = result.stderr.strip() or "unknown error"
        print(f"[FAIL] Ошибка запроса: {error_output}", file=sys.stderr)
        return 2

    stdout = result.stdout
    if status_marker not in stdout:
        print("[FAIL] Некорректный ответ от API")
        return 2

    body_part, status_part = stdout.rsplit(status_marker, 1)
    status_line = status_part.strip().splitlines()[0] if status_part.strip() else ""
    status_code = status_line or "0"
    body = body_part.strip()

    if not body:
        print("[FAIL] Некорректный ответ от API")
        return 2

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        print("[FAIL] Некорректный ответ от API")
        return 2

    if status_code == "403":
        print("[FAIL] Доступ запрещен (проверьте INTERNAL_API_KEY)")
        return 2
    if status_code != "200":
        print(f"[FAIL] Ошибка API: HTTP {status_code}")
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

