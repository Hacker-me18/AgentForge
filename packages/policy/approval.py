"""Human-in-the-loop approval storage and coordination."""

import asyncio
import time

import aiosqlite

from packages.policy.models import Approval, ApprovalStatus

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    decided_at REAL
)
"""


class ApprovalStore:
    """SQLite-backed persistence for approval requests."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialized = False

    async def _ensure(self) -> None:
        if self._initialized:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(CREATE_TABLE)
            await db.commit()
        self._initialized = True

    async def create(self, approval: Approval) -> Approval:
        await self._ensure()
        import json

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO approvals VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    approval.id,
                    approval.run_id,
                    approval.tool_name,
                    json.dumps(approval.arguments, ensure_ascii=False),
                    approval.risk_level,
                    approval.reason,
                    approval.status.value,
                    approval.created_at,
                    approval.decided_at,
                ),
            )
            await db.commit()
        return approval

    async def get(self, approval_id: str) -> Approval | None:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM approvals WHERE id = ?", (approval_id,)
            )
            row = await cursor.fetchone()
        return self._to_approval(row) if row else None

    async def list(self, status: ApprovalStatus | None = None) -> list[Approval]:
        await self._ensure()
        query = "SELECT * FROM approvals"
        params: tuple = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status.value,)
        query += " ORDER BY created_at DESC"
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
        return [self._to_approval(row) for row in rows]

    async def decide(self, approval_id: str, approve: bool) -> Approval | None:
        await self._ensure()
        status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE approvals SET status = ?, decided_at = ? WHERE id = ? AND status = ?",
                (status.value, time.time(), approval_id, ApprovalStatus.PENDING.value),
            )
            await db.commit()
        if cursor.rowcount == 0:
            return None
        return await self.get(approval_id)

    @staticmethod
    def _to_approval(row: tuple) -> Approval:
        import json

        return Approval(
            id=row[0],
            run_id=row[1],
            tool_name=row[2],
            arguments=json.loads(row[3]),
            risk_level=row[4],
            reason=row[5],
            status=ApprovalStatus(row[6]),
            created_at=row[7],
            decided_at=row[8],
        )


class ApprovalManager:
    """Coordinates approval requests between the runtime and decision makers.

    The runtime awaits ``request_and_wait``; the UI (or a test) calls
    ``decide`` which wakes up the waiter with the outcome.
    """

    def __init__(self, store: ApprovalStore):
        self.store = store
        self._waiters: dict[str, tuple[asyncio.Event, bool]] = {}

    async def request_and_wait(
        self,
        *,
        run_id: str,
        tool_name: str,
        arguments: dict,
        risk_level: str = "high",
        reason: str = "",
        timeout: float = 600.0,
    ) -> bool:
        approval = await self.store.create(
            Approval(
                run_id=run_id,
                tool_name=tool_name,
                arguments=arguments,
                risk_level=risk_level,
                reason=reason,
            )
        )
        event = asyncio.Event()
        self._waiters[approval.id] = (event, False)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except TimeoutError:
            await self.store.decide(approval.id, approve=False)
            return False
        finally:
            self._waiters.pop(approval.id, None)
        stored = await self.store.get(approval.id)
        return stored is not None and stored.status == ApprovalStatus.APPROVED

    async def decide(self, approval_id: str, approve: bool) -> Approval | None:
        approval = await self.store.decide(approval_id, approve)
        if approval is not None:
            waiter = self._waiters.get(approval_id)
            if waiter is not None:
                event, _ = waiter
                self._waiters[approval_id] = (event, approve)
                event.set()
        return approval
