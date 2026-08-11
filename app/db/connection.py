"""Подключение к SQLite и базовые операции."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite

from app.db.schema import SCHEMA_SQL

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "bot.db"

_db: Database | None = None


class Database:
    """Обёртка над aiosqlite."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("База данных не подключена")
        return self._conn

    async def execute(
        self, sql: str, params: tuple[Any, ...] | list[Any] = ()
    ) -> aiosqlite.Cursor:
        cur = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cur

    async def executemany(
        self, sql: str, seq: list[tuple[Any, ...]]
    ) -> aiosqlite.Cursor:
        cur = await self.conn.executemany(sql, seq)
        await self.conn.commit()
        return cur

    async def fetchone(
        self, sql: str, params: tuple[Any, ...] | list[Any] = ()
    ) -> aiosqlite.Row | None:
        cur = await self.conn.execute(sql, params)
        return await cur.fetchone()

    async def fetchall(
        self, sql: str, params: tuple[Any, ...] | list[Any] = ()
    ) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(sql, params)
        return await cur.fetchall()

    async def with_transaction(self) -> aiosqlite.Connection:
        """Возвращает соединение; вызывающий код управляет commit/rollback."""
        return self.conn


async def init_db(path: str | Path | None = None) -> Database:
    global _db
    db = Database(path or DEFAULT_DB_PATH)
    await db.connect()
    _db = db
    return db


def get_db() -> Database:
    if _db is None:
        raise RuntimeError("База данных не инициализирована")
    return _db
