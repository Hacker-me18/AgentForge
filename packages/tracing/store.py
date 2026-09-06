"""SQLite-backed event store."""

from __future__ import annotations

import json
from typing import Any, cast

import aiosqlite

from packages.tracing.events import Event

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    type TEXT NOT NULL,
    timestamp REAL NOT NULL,
    sequence INTEGER NOT NULL,
    payload TEXT NOT NULL
)
"""
CREATE_INDEX = "CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, sequence)"


class EventStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialized = False
        self._sequences: dict[str, int] = {}

    async def _ensure(self) -> None:
        if self._initialized:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(CREATE_TABLE)
            await db.execute(CREATE_INDEX)
            await db.commit()
        self._initialized = True

    def _next_sequence(self, run_id: str) -> int:
        seq = self._sequences.get(run_id, 0) + 1
        self._sequences[run_id] = seq
        return seq

    async def append(self, event: Event) -> Event:
        await self._ensure()
        event.sequence = self._next_sequence(event.run_id)
        async with aiosqlite.connect(self.db_path) as db:
            # Event writes are fire-and-forget from the runtime; wait for a
            # concurrent writer instead of surfacing SQLITE_BUSY.
            await db.execute("PRAGMA busy_timeout = 15000")
            await db.execute(
                "INSERT INTO events VALUES (?,?,?,?,?,?)",
                (
                    event.id,
                    event.run_id,
                    event.type,
                    event.timestamp,
                    event.sequence,
                    json.dumps(event.payload, ensure_ascii=False, default=str),
                ),
            )
            await db.commit()
        return event

    # Named for_run: a method called `list` shadows the builtin inside the class
    # body and breaks later `list[...]` return annotations under mypy.
    async def for_run(self, run_id: str) -> list[Event]:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY sequence", (run_id,)
            )
            rows = await cursor.fetchall()
        return [self._to_event(cast(tuple[Any, ...], row)) for row in rows]

    async def list_recent(self, limit: int = 100) -> list[Event]:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
        return [self._to_event(cast(tuple[Any, ...], row)) for row in rows]

    async def type_counts(self) -> dict[str, int]:
        """Event count per type (feeds the overview activity panel)."""
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT type, COUNT(*) FROM events GROUP BY type ORDER BY 2 DESC"
            )
            rows = cast(list[tuple[Any, ...]], await cursor.fetchall())
        return {str(row[0]): int(row[1]) for row in rows}

    async def tool_counts(self, limit: int = 400) -> dict[str, int]:
        """Executed-tool counts over the most recent ``tool.request`` events."""
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT payload FROM events WHERE type = 'tool.request'"
                " ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            rows = cast(list[tuple[Any, ...]], await cursor.fetchall())
        counts: dict[str, int] = {}
        for row in rows:
            try:
                tool = json.loads(str(row[0])).get("tool")
            except json.JSONDecodeError:
                continue
            if isinstance(tool, str):
                counts[tool] = counts.get(tool, 0) + 1
        return counts

    @staticmethod
    def _to_event(row: tuple[Any, ...]) -> Event:
        return Event(
            id=row[0],
            run_id=row[1],
            type=row[2],
            timestamp=row[3],
            sequence=row[4],
            payload=json.loads(row[5]),
        )
