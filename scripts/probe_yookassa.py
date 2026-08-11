"""Проверка доступа к API ЮKassa с машины, где крутится бот."""

from __future__ import annotations

import asyncio
import sys

import httpx


async def main() -> int:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://api.yookassa.ru")
        print(f"OK: HTTP {response.status_code}")
        return 0
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
