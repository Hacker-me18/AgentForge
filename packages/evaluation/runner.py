"""Offline evaluation runner.

Runs every case in a :class:`~packages.evaluation.dataset.Dataset` against one
:class:`AgentSpec`, mirroring the production composition in
``apps.api.run_service.RunService`` (registry + gateway + harness + runtime +
budget + policy) but kept fully offline:

- events are collected through a plain synchronous recorder into memory instead
  of an async ``EventBus`` + SQLite ``EventStore`` - no temp DB, no background
  task, deterministic ordering;
- ``python.execute`` still routes through ``SandboxRunner`` but is never
  invoked by the mock routing used here;
- approvals are auto-approved unless an ``AgentSpec`` policy denies the call.

The LLM is injected: pass a real provider for online evals, otherwise the spec
is turned into a deterministic :class:`MockLLMProvider` (``strategy``/``model``).
"""

import time
from typing import Any

from pydantic import BaseModel

from packages.context.engine import ContextEngine
from packages.evaluation.dataset import Case, Dataset
from packages.evaluation.metrics import RunResult, ScoreLimits, score_metrics
from packages.evaluation.report import EvaluationReport
from packages.llm.base import LLMProvider
from packages.llm.providers.mock import MockLLMProvider
from packages.policy.budget import Budget
from packages.policy.engine import PolicyEngine
from packages.policy.models import DEFAULT_RULES, PolicyRule
from packages.runtime.execution import AgentRuntime
from packages.runtime.harness import AgentHarness
from packages.sandbox.runner import SandboxRunner
from packages.tools.gateway.gateway import ToolGateway
from packages.tools.registry.builtin import create_default_registry
from packages.tracing.events import Event
from packages.tracing.trace import TraceBuilder


class AgentSpec(BaseModel):
    """A versioned agent configuration; one arm of an evaluation or A/B test."""

    name: str = "v1.0"
    agent_id: str = "research-agent"
    model: str = "mock-model"
    # Deterministic mock behaviour: "route" routes non-arithmetic tasks to
    # web.search (and arithmetic to calculator); "echo" always calls mock.echo.
    strategy: str = "route"
    system_prompt: str | None = None
    max_steps: int = 16
    max_cost: float = 0.5
    max_latency_s: float = 60.0
    # Optional partial override of the default governance table, e.g.
    # [{"tool": "web.search", "action": "deny", "reason": "..."}].
    policy_rules: list[dict[str, Any]] | None = None


class _Sink:
    """Synchronous event recorder compatible with harness/gateway/sandbox."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._records: list[tuple[str, dict, float]] = []

    def record(self, event_type: str, payload: dict) -> None:
        self._records.append((event_type, payload, time.time()))

    def events(self) -> list[Event]:
        return [
            Event(
                run_id=self.run_id,
                type=event_type,
                payload=payload,
                timestamp=timestamp,
                sequence=index,
            )
            for index, (event_type, payload, timestamp) in enumerate(self._records, start=1)
        ]


async def _always_approve(call_id: str, name: str, arguments: dict) -> bool:
    del call_id, name, arguments  # evaluation auto-approves by default
    return True


def build_policy_engine(spec: AgentSpec) -> PolicyEngine:
    """Default policy, overridden per-tool by ``spec.policy_rules``."""
    if not spec.policy_rules:
        return PolicyEngine()
    rules = {rule.tool: rule for rule in DEFAULT_RULES}
    for entry in spec.policy_rules:
        rules[entry["tool"]] = PolicyRule.model_validate(entry)
    return PolicyEngine(list(rules.values()))


class EvaluationRunner:
    """Executes cases offline and produces an :class:`EvaluationReport`."""

    def __init__(self, llm: LLMProvider | None = None):
        self._llm = llm

    def _provider(self, spec: AgentSpec) -> LLMProvider:
        if self._llm is not None:
            return self._llm
        return MockLLMProvider(model=spec.model, strategy=spec.strategy)

    async def run_case(
        self, case: Case, spec: AgentSpec, *, run_id: str | None = None
    ) -> RunResult:
        run_id = run_id or f"eval-{case.id}"
        sink = _Sink(run_id)
        sandbox_runner = SandboxRunner(event_recorder=sink.record)
        registry = create_default_registry(sandbox_runner=sandbox_runner)
        gateway = ToolGateway(registry, event_recorder=sink.record)
        harness = AgentHarness(
            self._provider(spec),
            tool_gateway=gateway,
            context_engine=ContextEngine(),
            event_recorder=sink.record,
            policy_engine=build_policy_engine(spec),
        )
        runtime = AgentRuntime(
            harness,
            approval_handler=_always_approve,
            budget=Budget(
                max_steps=spec.max_steps,
                max_cost=spec.max_cost,
                max_latency_s=spec.max_latency_s,
            ),
        )
        state = await harness.prepare(
            case.task,
            {
                "run_id": run_id,
                "agent_id": spec.agent_id,
                "system_prompt": spec.system_prompt,
            },
        )
        started = time.perf_counter()
        state = await runtime.run(state)
        latency_ms = (time.perf_counter() - started) * 1000.0

        events = sink.events()
        trace = TraceBuilder().build(events)
        result = RunResult(
            case=case,
            spec_name=spec.name,
            run_id=run_id,
            state=state,
            events=events,
            trace=trace,
            latency_ms=latency_ms,
        )
        score_metrics(
            result,
            ScoreLimits(
                max_steps=spec.max_steps,
                max_cost=spec.max_cost,
                max_latency_s=spec.max_latency_s,
            ),
        )
        return result

    async def evaluate(self, dataset: Dataset, spec: AgentSpec) -> EvaluationReport:
        results = []
        for case in dataset.cases:
            results.append(await self.run_case(case, spec))
        report = EvaluationReport(dataset_name=dataset.name, spec_name=spec.name, results=results)
        return report
