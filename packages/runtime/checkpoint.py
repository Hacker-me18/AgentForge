"""SQLite checkpoint store for agent run states (plain aiosqlite, no ORM)."""

import os
from datetime import UTC, datetime
from typing import Any, cast

import aiosqlite

from packages.runtime.state import AgentState

DEFAULT_DB_PATH = "data/agentos.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS checkpoints (
    run_id TEXT NOT NULL,
    step INTEGER NOT NULL,
    state_json TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


class CheckpointStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    @staticmethod
    async def _ensure_table(db: aiosqlite.Connection) -> None:
        await db.execute(_CREATE_TABLE)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_checkpoints_run ON checkpoints(run_id, step)"
        )
        await db.commit()

    async def save(self, state: AgentState) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA busy_timeout = 15000")
            await self._ensure_table(db)
            await db.execute(
                "INSERT INTO checkpoints (run_id, step, state_json, created_at)"
                " VALUES (?, ?, ?, ?)",
                (state.run_id, state.step, state.model_dump_json(), datetime.now(UTC).isoformat()),
            )
            await db.commit()

    async def _latest_row(self, run_id: str) -> tuple[Any, ...] | None:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            cursor = await db.execute(
                "SELECT step, state_json, created_at FROM checkpoints"
                " WHERE run_id = ? ORDER BY rowid DESC LIMIT 1",
                (run_id,),
            )
            row = await cursor.fetchone()
            # aiosqlite types rows opaquely; our SELECT columns map by position.
            return cast(tuple[Any, ...] | None, row)

    async def load(self, run_id: str) -> AgentState | None:
        row = await self._latest_row(run_id)
        if row is None:
            return None
        return AgentState.model_validate_json(row[1])

    async def latest(self, run_id: str) -> dict | None:
        row = await self._latest_row(run_id)
        if row is None:
            return None
        return {"run_id": run_id, "step": row[0], "created_at": row[2]}
