"""Run lifecycle service: starts agent runs and persists their records."""

import asyncio
import re
import time
import uuid
from typing import Any, cast

import aiosqlite

from agents.catalog import AgentInfo, get_agent
from packages.context.engine import ContextEngine
from packages.llm.base import LLMProvider, LLMResponse, ToolCall
from packages.llm.providers.mock import MockLLMProvider
from packages.policy.approval import ApprovalManager
from packages.policy.budget import Budget
from packages.policy.engine import PolicyEngine
from packages.runtime.checkpoint import CheckpointStore
from packages.runtime.execution import AgentRuntime
from packages.runtime.harness import AgentHarness
from packages.runtime.state import AgentState, RunStatus
from packages.sandbox.runner import SandboxRunner
from packages.tools.gateway.gateway import ToolGateway
from packages.tools.registry.builtin import create_default_registry
from packages.tracing.bus import EventBus

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    task TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    answer TEXT,
    steps INTEGER NOT NULL DEFAULT 0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0.0,
    created_at REAL NOT NULL,
    finished_at REAL
)
"""

# Same shape as packages/llm/providers/mock.py so `data-analyst` / free-form
# arithmetic tasks keep resolving to the calculator.
_ARITHMETIC_RE = re.compile(r"\d+(?:\.\d+)?(?:\s*[-+*/]\s*\d+(?:\.\d+)?)+")


def _plan_arguments(tool: str, task: str) -> dict:
    """Deterministic arguments for one step of a ``data-writer``-style plan."""
    if tool == "web.search":
        return {"query": task}
    if tool == "calculator":
        match = _ARITHMETIC_RE.search(task)
        return {"expression": match.group(0) if match else "3 * 7"}
    if tool == "database.write":
        note = task.replace("'", " ")[:140]
        return {"query": f"INSERT INTO demo_log (note) VALUES ('{note}')"}
    return {}


class RunStore:
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

    async def create(self, run_id: str, agent_id: str, task: str) -> None:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA busy_timeout = 15000")
            await db.execute(
                "INSERT INTO runs (run_id, agent_id, task, status, created_at) VALUES (?,?,?,?,?)",
                (run_id, agent_id, task, "pending", time.time()),
            )
            await db.commit()

    async def update_from_state(self, state: AgentState, *, finished: bool = True) -> None:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA busy_timeout = 15000")
            if finished:
                await db.execute(
                    "UPDATE runs SET status=?, error=?, answer=?, steps=?, input_tokens=?,"
                    " output_tokens=?, cost=?, finished_at=? WHERE run_id=?",
                    (
                        state.status.value,
                        state.error,
                        state.context.get("final_answer"),
                        state.step,
                        state.token_usage.get("input", 0),
                        state.token_usage.get("output", 0),
                        state.cost,
                        time.time(),
                        state.run_id,
                    ),
                )
            else:
                # Progress heartbeat: persist the live status without stamping a
                # completion time (the run is still waiting on a human / running).
                await db.execute(
                    "UPDATE runs SET status=?, error=?, answer=?, steps=?, input_tokens=?,"
                    " output_tokens=?, cost=? WHERE run_id=?",
                    (
                        state.status.value,
                        state.error,
                        state.context.get("final_answer"),
                        state.step,
                        state.token_usage.get("input", 0),
                        state.token_usage.get("output", 0),
                        state.cost,
                        state.run_id,
                    ),
                )
            await db.commit()

    async def get(self, run_id: str) -> dict | None:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,))
            row = await cursor.fetchone()
        return self._to_dict(cast(tuple[Any, ...], row)) if row else None

    async def list(self, limit: int = 50) -> list[dict]:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
        return [self._to_dict(cast(tuple[Any, ...], row)) for row in rows]

    async def aggregate(self) -> dict:
        """Headline numbers for the overview page (single GROUP BY query)."""
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT status, COUNT(*) FROM runs GROUP BY status")
            rows = cast(list[tuple[Any, ...]], await cursor.fetchall())
            totals = await db.execute(
                "SELECT COUNT(*), COALESCE(SUM(steps),0), COALESCE(SUM(cost),0),"
                " COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0)"
                " FROM runs"
            )
            total_row = cast(tuple[Any, ...], await totals.fetchone())
            timeline = await db.execute(
                "SELECT strftime('%Y-%m-%d', created_at, 'unixepoch', 'localtime') AS day,"
                " COUNT(*) FROM runs GROUP BY day ORDER BY day DESC LIMIT 30"
            )
            by_day = cast(list[tuple[Any, ...]], await timeline.fetchall())
        by_status = {str(row[0]): int(row[1]) for row in rows}
        total = int(total_row[0])
        return {
            "total": total,
            "by_status": by_status,
            "steps": int(total_row[1]),
            "cost": round(float(total_row[2]), 6),
            "input_tokens": int(total_row[3]),
            "output_tokens": int(total_row[4]),
            "total_tokens": int(total_row[3]) + int(total_row[4]),
            "timeline": [{"day": str(day), "runs": int(count)} for day, count in by_day],
        }

    @staticmethod
    def _to_dict(row: tuple[Any, ...]) -> dict:
        return {
            "run_id": row[0],
            "agent_id": row[1],
            "task": row[2],
            "status": row[3],
            "error": row[4],
            "answer": row[5],
            "steps": row[6],
            "input_tokens": row[7],
            "output_tokens": row[8],
            "cost": row[9],
            "created_at": row[10],
            "finished_at": row[11],
        }


class RunService:
    """Composes runtime components per run and tracks their lifecycle."""

    def __init__(
        self,
        *,
        db_path: str,
        llm: LLMProvider,
        policy_engine: PolicyEngine,
        approval_manager: ApprovalManager,
        event_bus: EventBus,
    ):
        self.db_path = db_path
        self.llm = llm
        self.policy_engine = policy_engine
        self.approval_manager = approval_manager
        self.event_bus = event_bus
        self.store = RunStore(db_path)
        self._tasks: dict[str, asyncio.Task] = {}
        self._runtimes: dict[str, AgentRuntime] = {}

    async def start(
        self,
        task: str,
        *,
        agent_id: str = "default-agent",
        system_prompt: str | None = None,
        max_steps: int = 16,
    ) -> dict:
        run_id = uuid.uuid4().hex[:8]
        agent = get_agent(agent_id)
        recorder = self.event_bus.recorder(run_id)
        sandbox_runner = SandboxRunner(event_recorder=recorder)
        registry = create_default_registry(sandbox_runner=sandbox_runner)
        gateway = ToolGateway(registry, event_recorder=recorder)
        harness = AgentHarness(
            self._run_llm(agent, task),
            tool_gateway=gateway,
            context_engine=ContextEngine(),
            event_recorder=recorder,
            policy_engine=self.policy_engine,
        )

        async def approval_handler(call_id: str, name: str, arguments: dict) -> bool:
            return await self.approval_manager.request_and_wait(
                run_id=run_id, tool_name=name, arguments=arguments
            )

        runtime = AgentRuntime(
            harness,
            checkpoint=CheckpointStore(self.db_path),
            approval_handler=approval_handler,
            budget=Budget(max_steps=max_steps, max_cost=0.5),
        )
        state = await harness.prepare(
            task,
            {"run_id": run_id, "agent_id": agent_id, "system_prompt": system_prompt},
        )
        await self.store.create(run_id, agent_id, task)
        if agent is not None and "database.write" in agent.plan:
            await self._ensure_ledger()
        self._runtimes[run_id] = runtime
        self._tasks[run_id] = asyncio.create_task(self._execute(runtime, state))
        record = await self.store.get(run_id)
        assert record is not None
        return record

    async def _execute(self, runtime: AgentRuntime, state: AgentState) -> None:
        # Run in a task so we can watch the live status and persist transitions
        # (running → waiting_approval) the moment they happen — otherwise a run
        # parked on a human decision would stay "pending" in the database.
        task = asyncio.create_task(runtime.run(state))
        persisted: RunStatus | None = None
        try:
            while not task.done():
                status = state.status
                if status != persisted and status in (
                    RunStatus.RUNNING,
                    RunStatus.WAITING_APPROVAL,
                ):
                    await self.store.update_from_state(state, finished=False)
                    persisted = status
                await asyncio.sleep(0.05)
            try:
                await task
            except Exception as exc:  # defensive: run() already captures errors
                state.error = str(exc)
                if state.status not in (
                    RunStatus.COMPLETED,
                    RunStatus.FAILED,
                    RunStatus.CANCELLED,
                    RunStatus.BUDGET_EXCEEDED,
                ):
                    state.status = RunStatus.FAILED
        finally:
            await self.event_bus.flush()
            await self.store.update_from_state(state, finished=True)

    def cancel(self, run_id: str) -> bool:
        runtime = self._runtimes.get(run_id)
        if runtime is None:
            return False
        runtime.cancel(run_id)
        return True

    # -- per-agent demo behaviour ------------------------------------------

    def _run_llm(self, agent: AgentInfo | None, task: str) -> LLMProvider:
        """Shape the LLM used for a run.

        Real providers (deepseek / openai) are returned unchanged — the catalog
        only selects deterministic behaviour for the mock provider used by
        demos, offline evals and local runs. An unknown ``agent_id`` keeps the
        original behaviour (``mock.echo``) for backwards compatibility.
        """
        if not isinstance(self.llm, MockLLMProvider):
            return self.llm
        model = getattr(self.llm, "_model", "mock-model")
        if agent is None:
            return self.llm
        if not agent.plan:
            return MockLLMProvider(model=model, strategy=agent.strategy or "route")
        scripted = [
            LLMResponse(
                content="",
                model=model,
                input_tokens=8,
                output_tokens=8,
                finish_reason="tool_calls",
                tool_calls=[
                    ToolCall(
                        id=f"mock-{index}",
                        name=tool,
                        arguments=_plan_arguments(tool, task),
                    )
                ],
            )
            for index, tool in enumerate(agent.plan)
        ]
        # Once the scripted calls are consumed the provider falls back to its
        # default final-summary path, echoing the *real* last tool result.
        return MockLLMProvider(scripted=scripted, model=model)

    async def _ensure_ledger(self) -> None:
        """Create the ``demo_log`` table the data-writer agent writes into."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA busy_timeout = 15000")
            await db.execute(
                "CREATE TABLE IF NOT EXISTS demo_log ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " note TEXT NOT NULL,"
                " created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            await db.commit()
