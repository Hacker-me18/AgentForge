"""Seed the local Studio database with a deterministic example dataset.

Deletes ``data/agentos.db`` and runs a curated set of tasks through the same
composition the API uses (registry + gateway + harness + runtime + budget +
policy + approval + events). Everything you see afterwards in the UI is data
produced by an actual run: no rows are hand-inserted except the human decision
on the data-writer approval, which is what a reviewer would click.

Usage::

    python scripts/seed_demo.py

The mock LLM is configured with the DeepSeek pricing model so runs accrue real
(non-zero, estimated) token and cost figures for the dashboards.
"""

import asyncio
import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from agents.catalog import get_agent  # noqa: E402
from apps.api.run_service import RunService  # noqa: E402
from packages.llm.providers.mock import MockLLMProvider  # noqa: E402
from packages.policy.approval import ApprovalManager, ApprovalStore  # noqa: E402
from packages.policy.engine import PolicyEngine  # noqa: E402
from packages.policy.models import ApprovalStatus  # noqa: E402
from packages.tracing.bus import EventBus  # noqa: E402
from packages.tracing.store import EventStore  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "agentos.db"


async def _wait_run(service: RunService, run_id: str) -> dict:
    """Poll until a background run reaches a terminal state."""
    for _ in range(3000):
        record = await service.store.get(run_id)
        if record is not None and record["status"] not in (
            "pending",
            "running",
            "waiting_approval",
        ):
            return record
        await asyncio.sleep(0.02)
    raise TimeoutError(f"run {run_id} did not finish in time")


async def main() -> int:
    # Never destroy prior data: the previous database is moved to a dated
    # backup (gitignored: data/*.db) before a fresh one is seeded.
    if DB_PATH.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = DB_PATH.parent / f"{DB_PATH.stem}.seed.{stamp}.bak.db"
        DB_PATH.rename(backup)
        print(f"backed up previous database to {backup.name}")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = str(DB_PATH)
    # The event bus writes fire-and-forget while runs/approvals/tools also
    # write, so put the database in WAL mode with a generous busy timeout to
    # avoid SQLITE_BUSY on the data-writer (approval) run.
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=15000")
    finally:
        conn.close()

    approval_store = ApprovalStore(db)
    service = RunService(
        db_path=db,
        llm=MockLLMProvider(model="deepseek-chat", strategy="route"),
        policy_engine=PolicyEngine(),
        approval_manager=ApprovalManager(approval_store),
        event_bus=EventBus(EventStore(db)),
    )

    # Auto-decider: approve anything the data-writer agent asks for, the same
    # way a reviewer clicking "Approve" in the UI would.
    stop = asyncio.Event()

    async def decider() -> None:
        while not stop.is_set():
            for approval in await approval_store.list(ApprovalStatus.PENDING):
                await service.approval_manager.decide(approval.id, approve=True)
            await asyncio.sleep(0.03)

    decider_task = asyncio.create_task(decider())

    runs: list[dict] = []
    started = time.perf_counter()

    async def run_task(agent_id: str, task: str) -> None:
        record = await service.start(task=task, agent_id=agent_id, max_steps=8)
        runs.append(await _wait_run(service, record["run_id"]))

    research = get_agent("research-agent")
    analyst = get_agent("data-analyst")
    writer = get_agent("data-writer")
    assert research is not None and analyst is not None and writer is not None

    print(f"seeding {len(research.suggested_tasks[:5])} research runs …")
    for task in research.suggested_tasks[:5]:
        await run_task("research-agent", task)
    print(f"seeding {len(analyst.suggested_tasks[:3])} analyst runs …")
    for task in analyst.suggested_tasks[:3]:
        await run_task("data-analyst", task)
    print("seeding 1 data-writer (approval) run …")
    await run_task("data-writer", writer.suggested_tasks[0])

    stop.set()
    await decider_task
    elapsed = time.perf_counter() - started

    print("\nseeded runs:")
    print(f"{'run_id':10} {'agent':16} {'status':16} {'steps':>5} {'cost':>10} task")
    for run in runs:
        answer = str(run["answer"])[:40].replace("\n", " ")
        print(
            f"{run['run_id']:10} {run['agent_id']:16} {run['status']:16}"
            f" {run['steps']:>5} {run['cost']:>10.6f}  {answer}"
        )
    print(
        f"\ndone in {elapsed:.1f}s → {len(runs)} runs, "
        f"{len([a for a in runs if a['status'] == 'completed'])} completed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
