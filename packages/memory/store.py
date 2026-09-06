"""Minimal memory store: per-instance short-term dict + SQLite long-term table."""

import json
import os
from datetime import UTC, datetime
from typing import Any

import aiosqlite

DEFAULT_DB_PATH = "data/agentos.db"


class MemoryStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.short_term: dict[str, Any] = {}
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    @staticmethod
    async def _ensure_table(db: aiosqlite.Connection) -> None:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS memory ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        await db.commit()

    async def get(self, key: str, default: Any = None) -> Any:
        if key in self.short_term:
            return self.short_term[key]
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            cursor = await db.execute("SELECT value FROM memory WHERE key = ?", (key,))
            row = await cursor.fetchone()
        if row is None:
            return default
        return json.loads(row[0])

    async def set(self, key: str, value: Any, *, long_term: bool = True) -> None:
        if not long_term:
            self.short_term[key] = value
            return
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            await db.execute(
                "INSERT INTO memory (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET"
                " value = excluded.value, updated_at = excluded.updated_at",
                (
                    key,
                    json.dumps(value, ensure_ascii=False, default=str),
                    datetime.now(UTC).isoformat(),
                ),
            )
            await db.commit()

    async def forget(self, key: str) -> None:
        self.short_term.pop(key, None)
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            await db.execute("DELETE FROM memory WHERE key = ?", (key,))
            await db.commit()
