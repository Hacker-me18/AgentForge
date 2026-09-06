"""Phase E tests: policy engine, budget control and human approval."""

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from packages.llm.base import LLMResponse, ToolCall
from packages.llm.providers.mock import MockLLMProvider
from packages.policy.approval import ApprovalManager, ApprovalStore
from packages.policy.budget import Budget
from packages.policy.engine import PolicyEngine
from packages.policy.models import Approval, ApprovalStatus, PolicyAction, PolicyRule
from packages.runtime.execution import AgentRuntime
from packages.runtime.harness import AgentHarness
from packages.runtime.state import RunStatus


class _StubGateway:
    def schemas(self) -> list[dict]:
        return []

    async def call(self, name: str, arguments: dict) -> dict:
        return {"status": "success", "output": {"tool": name, "args": arguments}}


def _scripted_llm(tool_name: str) -> MockLLMProvider:
    return MockLLMProvider(
        scripted=[
            LLMResponse(
                content="",
                tool_calls=[ToolCall(id="c1", name=tool_name, arguments={"q": 1})],
                model="mock-model",
                input_tokens=10,
                output_tokens=5,
                finish_reason="tool_calls",
            ),
            LLMResponse(
                content="done",
                tool_calls=[],
                model="mock-model",
                input_tokens=10,
                output_tokens=5,
                finish_reason="stop",
            ),
        ]
    )


# ---------------------------------------------------------------------------
# policy engine: ALLOW / DENY / REQUIRE_APPROVAL
# ---------------------------------------------------------------------------


def test_engine_three_actions() -> None:
    engine = PolicyEngine()
    assert engine.check("web.search") == PolicyAction.ALLOW
    assert engine.check("shell.execute") == PolicyAction.DENY
    assert engine.check("database.write") == PolicyAction.REQUIRE_APPROVAL
    # Unknown tool defaults to require_approval (fail-closed).
    assert engine.check("unknown.tool") == PolicyAction.REQUIRE_APPROVAL


def test_engine_set_rule() -> None:
    engine = PolicyEngine(rules=[])
    engine.set_rule(PolicyRule(tool="custom.tool", action=PolicyAction.ALLOW))
    assert engine.check("custom.tool") == PolicyAction.ALLOW


# ---------------------------------------------------------------------------
# budget control
# ---------------------------------------------------------------------------


def test_budget_dimensions() -> None:
    budget = Budget(max_steps=5, max_tokens=100, max_cost=0.5, max_latency_s=10)
    assert budget.exceeded(step=5, tokens=0, cost=0.0, elapsed_s=0.0) is not None
    assert budget.exceeded(step=0, tokens=150, cost=0.0, elapsed_s=0.0) is not None
    assert budget.exceeded(step=0, tokens=0, cost=0.6, elapsed_s=0.0) is not None
    assert budget.exceeded(step=0, tokens=0, cost=0.0, elapsed_s=11.0) is not None
    assert budget.exceeded(step=1, tokens=10, cost=0.1, elapsed_s=1.0) is None


async def test_runtime_budget_tokens_exceeded() -> None:
    # LLM keeps requesting tool calls; token budget (25) hit after 2 steps.
    llm = MockLLMProvider(
        scripted=[
            LLMResponse(
                content="",
                tool_calls=[ToolCall(id=f"c{i}", name="mock.echo", arguments={})],
                model="mock-model",
                input_tokens=10,
                output_tokens=5,
                finish_reason="tool_calls",
            )
            for i in range(10)
        ]
    )
    harness = AgentHarness(llm=llm, tool_gateway=_StubGateway())
    runtime = AgentRuntime(harness=harness, budget=Budget(max_steps=50, max_tokens=25))
    state = await harness.prepare("task")
    state = await runtime.run(state)
    assert state.status == RunStatus.BUDGET_EXCEEDED
    assert "token budget" in (state.error or "")


# ---------------------------------------------------------------------------
# approval store + manager
# ---------------------------------------------------------------------------


async def test_approval_manager_approve_and_reject(tmp_path) -> None:
    store = ApprovalStore(str(tmp_path / "approvals.db"))
    manager = ApprovalManager(store)

    async def wait_pending() -> Approval:
        # Poll until the request's row commits (writes are async). Once the row
        # is visible the waiter is guaranteed registered (see request_and_wait).
        for _ in range(100):
            pending = await store.list(ApprovalStatus.PENDING)
            if pending:
                return pending[0]
            await asyncio.sleep(0.01)
        raise AssertionError("approval request never became visible")

    # Approve path.
    waiter = asyncio.create_task(
        manager.request_and_wait(run_id="r1", tool_name="database.write", arguments={})
    )
    approval = await wait_pending()
    assert approval.tool_name == "database.write"
    await manager.decide(approval.id, approve=True)
    assert await waiter is True
    stored = await store.get(approval.id)
    assert stored is not None and stored.status == ApprovalStatus.APPROVED

    # Reject path.
    waiter = asyncio.create_task(
        manager.request_and_wait(run_id="r1", tool_name="database.write", arguments={})
    )
    approval = await wait_pending()
    await manager.decide(approval.id, approve=False)
    assert await waiter is False
    stored = await store.get(approval.id)
    assert stored is not None and stored.status == ApprovalStatus.REJECTED

    # Second decide on decided approval is a no-op.
    assert await manager.decide(approval.id, True) is None


async def test_approval_timeout_rejects(tmp_path) -> None:
    store = ApprovalStore(str(tmp_path / "approvals.db"))
    manager = ApprovalManager(store)
    approved = await manager.request_and_wait(
        run_id="r1", tool_name="database.write", arguments={}, timeout=0.1
    )
    assert approved is False
    stored = (await store.list())[0]
    assert stored.status == ApprovalStatus.REJECTED


# ---------------------------------------------------------------------------
# runtime integration: require_approval pauses and waits for the decision
# ---------------------------------------------------------------------------


async def test_runtime_approval_flow(tmp_path) -> None:
    store = ApprovalStore(str(tmp_path / "approvals.db"))
    manager = ApprovalManager(store)

    async def handler(call_id: str, name: str, arguments: dict) -> bool:
        return await manager.request_and_wait(run_id="r-test", tool_name=name, arguments=arguments)

    harness = AgentHarness(
        llm=_scripted_llm("database.write"),
        tool_gateway=_StubGateway(),
        policy_engine=PolicyEngine(),
    )
    runtime = AgentRuntime(harness=harness, approval_handler=handler)
    state = await harness.prepare("update records")
    run_task = asyncio.create_task(runtime.run(state))

    # The run must pause in WAITING_APPROVAL until we approve it.
    for _ in range(50):
        await asyncio.sleep(0.02)
        if state.status == RunStatus.WAITING_APPROVAL:
            break
    assert state.status == RunStatus.WAITING_APPROVAL

    # The status flips before the approval row is written by the handler's
    # async store.create, so poll for the row instead of asserting a single
    # read (which is racy once the runtime schedules the handler).
    pending: list = []
    for _ in range(50):
        pending = await store.list(ApprovalStatus.PENDING)
        if pending:
            break
        await asyncio.sleep(0.02)
    assert len(pending) == 1
    assert pending[0].tool_name == "database.write"
    await manager.decide(pending[0].id, approve=True)

    state = await asyncio.wait_for(run_task, timeout=5)
    assert state.status == RunStatus.COMPLETED
    assert any(o.get("tool") == "database.write" for o in state.observations)


async def test_runtime_approval_rejected_blocks_tool(tmp_path) -> None:
    store = ApprovalStore(str(tmp_path / "approvals.db"))
    manager = ApprovalManager(store)

    async def handler(call_id: str, name: str, arguments: dict) -> bool:
        # The runtime awaits us inline. Start the request, wait until its row is
        # visible (guaranteeing the waiter is registered), then reject it
        # deterministically - no fire-and-forget task racing store.create.
        request = asyncio.create_task(
            manager.request_and_wait(run_id="r-test", tool_name=name, arguments=arguments)
        )
        for _ in range(100):
            pending = await store.list(ApprovalStatus.PENDING)
            if pending:
                break
            await asyncio.sleep(0.01)
        assert pending, "approval request never became visible"
        await manager.decide(pending[-1].id, approve=False)
        return await request

    harness = AgentHarness(
        llm=_scripted_llm("database.write"),
        tool_gateway=_StubGateway(),
        policy_engine=PolicyEngine(),
    )
    runtime = AgentRuntime(harness=harness, approval_handler=handler)
    state = await harness.prepare("update records")
    state = await runtime.run(state)
    assert state.status == RunStatus.COMPLETED
    blocked = [
        o
        for o in state.observations
        if o.get("status") == "blocked" and o.get("tool") == "database.write"
    ]
    assert len(blocked) == 1
    assert "rejected" in blocked[0]["error"]


async def test_runtime_denied_tool_blocked() -> None:
    harness = AgentHarness(
        llm=_scripted_llm("shell.execute"),
        tool_gateway=_StubGateway(),
        policy_engine=PolicyEngine(),
    )
    runtime = AgentRuntime(harness=harness)
    state = await harness.prepare("do something dangerous")
    state = await runtime.run(state)
    assert state.status == RunStatus.COMPLETED
    blocked = [o for o in state.observations if o.get("status") == "blocked"]
    assert len(blocked) == 1
    assert "deny" in blocked[0]["error"]


# ---------------------------------------------------------------------------
# policy / approval API
# ---------------------------------------------------------------------------


async def test_policy_api() -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/policies")
            assert resp.status_code == 200
            rules = {r["tool"]: r["action"] for r in resp.json()}
            assert rules["database.write"] == "require_approval"
            assert rules["shell.execute"] == "deny"

            resp = await client.put(
                "/api/policies",
                json={"tool": "custom.tool", "action": "deny", "reason": "test"},
            )
            assert resp.status_code == 200
            rules = {r["tool"]: r["action"] for r in (await client.get("/api/policies")).json()}
            assert rules["custom.tool"] == "deny"


async def test_approval_api_decide() -> None:
    async with app.router.lifespan_context(app):
        manager = app.state.approval_manager
        # Unique run id so rows left behind by an earlier crashed run of this
        # test (the API store is a persistent shared DB) never collide.
        run_id = f"r-api-{uuid.uuid4().hex[:8]}"
        waiter = asyncio.create_task(
            manager.request_and_wait(run_id=run_id, tool_name="database.write", arguments={"a": 1})
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            pending = []
            for _ in range(100):
                resp = await client.get("/api/approvals", params={"status": "pending"})
                assert resp.status_code == 200
                pending = [row for row in resp.json() if row["run_id"] == run_id]
                if pending:
                    break
                await asyncio.sleep(0.02)
            assert len(pending) == 1
            assert pending[0]["tool_name"] == "database.write"

            resp = await client.post(f"/api/approvals/{pending[0]['id']}/approve")
            assert resp.status_code == 200
            assert resp.json()["status"] == "approved"

            # Deciding again -> 404.
            resp = await client.post(f"/api/approvals/{pending[0]['id']}/reject")
            assert resp.status_code == 404

        assert await waiter is True
