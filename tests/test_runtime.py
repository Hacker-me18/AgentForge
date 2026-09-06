"""Tests for the Phase B agent runtime core (mock only, no network)."""

import pytest

from apps.api.config import Settings
from packages.context.engine import ContextEngine
from packages.llm.base import LLMResponse, ToolCall
from packages.llm.factory import LLMFactory
from packages.llm.providers.mock import MockLLMProvider
from packages.runtime.checkpoint import CheckpointStore
from packages.runtime.execution import AgentRuntime
from packages.runtime.harness import AgentHarness
from packages.runtime.state import AgentState, RunStatus


class EchoGateway:
    def schemas(self) -> list[dict]:
        return [
            {
                "name": "echo",
                "description": "Echo back the input text",
                "parameters": {"type": "object", "properties": {"text": {"type": "string"}}},
            }
        ]

    async def call(self, name: str, arguments: dict) -> dict:
        return {"echo": arguments.get("text", "")}


class FlakyGateway(EchoGateway):
    def __init__(self) -> None:
        self.calls = 0

    async def call(self, name: str, arguments: dict) -> dict:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("transient boom")
        return {"echo": arguments.get("text", "")}


def tool_call_response(call_id: str = "c1", text: str = "hello") -> LLMResponse:
    return LLMResponse(
        content="",
        tool_calls=[ToolCall(id=call_id, name="echo", arguments={"text": text})],
        model="mock-model",
        input_tokens=10,
        output_tokens=5,
        finish_reason="tool_calls",
    )


def final_response(content: str = "final answer: hello") -> LLMResponse:
    return LLMResponse(
        content=content,
        model="mock-model",
        input_tokens=20,
        output_tokens=8,
        finish_reason="stop",
    )


def make_runtime(
    scripted: list[LLMResponse], gateway=None, **runtime_kwargs
) -> tuple[AgentHarness, AgentRuntime]:
    harness = AgentHarness(
        llm=MockLLMProvider(scripted=scripted), tool_gateway=gateway or EchoGateway()
    )
    return harness, AgentRuntime(harness=harness, **runtime_kwargs)


async def test_mock_end_to_end_completes() -> None:
    harness, runtime = make_runtime([tool_call_response(), final_response()])
    state = await harness.prepare(
        "say hello", {"agent_id": "test-agent", "system_prompt": "You are helpful."}
    )
    state = await runtime.run(state)

    assert state.status == RunStatus.COMPLETED
    assert state.step == 2
    assert state.token_usage == {"input": 30, "output": 13}
    assert state.cost == 0.0
    assert state.context["final_answer"]
    assert state.error is None


async def test_tool_retry_recovers() -> None:
    gateway = FlakyGateway()
    harness, runtime = make_runtime(
        [tool_call_response(), final_response()], gateway=gateway, max_retries=2
    )
    state = await runtime.run(await harness.prepare("flaky task", {}))

    assert state.status == RunStatus.COMPLETED
    assert gateway.calls == 2
    statuses = [o["status"] for o in state.observations]
    assert "failed" in statuses
    assert "success" in statuses
    assert statuses.index("failed") < statuses.index("success")


async def test_budget_exceeded_stops_run() -> None:
    scripted = [tool_call_response(call_id=f"c{i}") for i in range(3)]
    harness, runtime = make_runtime(scripted, max_steps=3)
    state = await runtime.run(await harness.prepare("loop forever", {}))

    assert state.status == RunStatus.BUDGET_EXCEEDED
    assert state.step == 3
    assert state.error


async def test_checkpoint_roundtrip(tmp_path) -> None:
    store = CheckpointStore(str(tmp_path / "checkpoints.db"))
    harness, runtime = make_runtime([tool_call_response(), final_response()], checkpoint=store)
    state = await runtime.run(await harness.prepare("checkpoint me", {}))

    loaded = await store.load(state.run_id)
    assert loaded is not None
    assert loaded.run_id == state.run_id
    assert loaded.status == RunStatus.COMPLETED
    assert loaded.step == state.step
    assert loaded.messages == state.messages

    meta = await store.latest(state.run_id)
    assert meta is not None
    assert meta["step"] == state.step

    assert await store.load("nonexistent-run") is None


def test_llm_factory_dispatch() -> None:
    provider = LLMFactory.create(Settings(llm_provider="mock"))
    assert isinstance(provider, MockLLMProvider)

    with pytest.raises(ValueError, match="Unknown LLM provider"):
        LLMFactory.create(Settings(llm_provider="no-such-provider"))


async def test_context_engine_compresses_within_budget() -> None:
    engine = ContextEngine(token_budget=500)
    state = AgentState(
        run_id="r1",
        agent_id="a",
        task="t",
        messages=[{"role": "user", "content": "x" * 3000} for _ in range(40)],
    )
    messages = await engine.build(
        state,
        system_prompt="You are a helpful assistant.",
        tool_schemas=[{"name": "echo", "description": "echo input"}],
    )

    assert engine.estimate(messages) <= 500
    assert messages[0]["role"] == "system"


async def test_cancellation() -> None:
    holder: dict = {}

    def recorder(event: str, payload: dict) -> None:
        if event == "observation":
            runtime.cancel(holder["run_id"])

    harness = AgentHarness(
        llm=MockLLMProvider(
            scripted=[tool_call_response(), tool_call_response("c2"), final_response()]
        ),
        tool_gateway=EchoGateway(),
        event_recorder=recorder,
    )
    runtime = AgentRuntime(harness=harness, max_steps=10)
    state = await harness.prepare("cancel me", {})
    holder["run_id"] = state.run_id

    state = await runtime.run(state)
    assert state.status == RunStatus.CANCELLED
