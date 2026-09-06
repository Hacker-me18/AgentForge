"""Evaluation dimensions: turn one executed case into 0..1 metric scores.

A single executed case is captured in :class:`RunResult` (state + flat events +
reconstructed trace). :func:`score_metrics` then produces the seven Phase G
dimensions defined in tasks.md 7.3:

``task_success`` ``tool_selection`` ``evidence`` ``policy`` ``latency``
``cost`` ``steps``

Every dimension returns a :class:`MetricScore` (a 0..1 score plus a detail
dict for transparency). The overall score for a case is the mean of the seven.

Data-source notes (verified against the runtime):

- Tool **results** are not present on ``tool.completed`` events or trace spans;
  they live on ``observation`` events (payload ``status``/``tool``/``result``)
  and in ``AgentState``. Evidence therefore reads observation payloads.
- **Policy violations** surface on ``observation`` events whose status is
  ``blocked`` with an error of the form ``policy decision: ...`` or
  ``approval rejected`` - the gateway is never reached for denied calls, so no
  ``policy.checked`` event exists for them.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from packages.evaluation.dataset import Case
from packages.runtime.state import AgentState
from packages.tracing.events import Event

# Ordered metric keys used for reporting; order is preserved everywhere.
DIMENSIONS: tuple[str, ...] = (
    "task_success",
    "tool_selection",
    "evidence",
    "policy",
    "latency",
    "cost",
    "steps",
)

DIMENSION_LABELS: dict[str, str] = {
    "task_success": "Task Success",
    "tool_selection": "Tool Selection",
    "evidence": "Evidence",
    "policy": "Policy",
    "latency": "Latency",
    "cost": "Cost",
    "steps": "Steps",
}

_VIOLATION_MARKERS = ("policy decision:", "approval rejected")


@dataclass
class ScoreLimits:
    """Budget/reference values used to normalise the bounded dimensions."""

    max_steps: int = 16
    max_cost: float = 0.5
    max_latency_s: float = 60.0


@dataclass
class MetricScore:
    name: str
    score: float
    detail: dict = field(default_factory=dict)


@dataclass
class RunResult:
    """Everything captured about one executed evaluation case."""

    case: Case
    spec_name: str
    run_id: str
    state: AgentState
    events: list[Event]
    trace: dict
    latency_ms: float
    metrics: dict[str, MetricScore] = field(default_factory=dict)

    # -- convenient views over state --------------------------------------

    @property
    def status(self) -> str:
        return self.state.status.value

    @property
    def answer(self) -> str:
        return self.state.context.get("final_answer") or ""

    @property
    def error(self) -> str | None:
        return self.state.error

    @property
    def steps(self) -> int:
        return self.state.step

    @property
    def cost(self) -> float:
        return self.state.cost

    @property
    def observation_payloads(self) -> list[dict]:
        return [e.payload for e in self.events if e.type == "observation"]


# ---------------------------------------------------------------------------
# feature derivation
# ---------------------------------------------------------------------------


def _successful_observations(result: RunResult) -> list[dict]:
    return [p for p in result.observation_payloads if p.get("status") == "success"]


def used_tools(result: RunResult) -> set[str]:
    """Names of tools that actually executed successfully."""
    return {p["tool"] for p in _successful_observations(result) if p.get("tool")}


def blocked_tools(result: RunResult) -> list[dict]:
    """Tool attempts that were stopped by the policy/governance layer."""
    violations = []
    for payload in result.observation_payloads:
        if payload.get("status") != "blocked":
            continue
        error = str(payload.get("error", ""))
        if any(marker in error for marker in _VIOLATION_MARKERS):
            violations.append({"tool": payload.get("tool"), "error": error})
    return violations


def evidence_corpus(result: RunResult) -> str:
    """Answer text plus the JSON text of every successful tool output."""
    chunks = [result.answer]
    for payload in _successful_observations(result):
        output = payload.get("result")
        if output is not None:
            chunks.append(json.dumps(output, ensure_ascii=False, default=str))
    return "\n".join(chunks)


# ---------------------------------------------------------------------------
# per-dimension scorers
# ---------------------------------------------------------------------------


def score_task_success(result: RunResult, case: Case) -> MetricScore:
    """The task counts as done when the run finished with an answer AND the
    agent actually performed its required actions (a run that only reports a
    policy block has not succeeded at the task)."""
    completed = result.status == "completed"
    has_answer = bool(result.answer.strip())
    expected = list(case.expected_tools)
    used = used_tools(result)
    required_used = all(tool in used for tool in expected) if expected else True
    succeeded = completed and has_answer and required_used
    return MetricScore(
        name="task_success",
        score=1.0 if succeeded else 0.0,
        detail={
            "status": result.status,
            "has_answer": has_answer,
            "required_tools_used": required_used,
            "error": result.error,
        },
    )


def score_tool_selection(result: RunResult, case: Case) -> MetricScore:
    used = used_tools(result)
    required = list(case.expected_tools)
    matched = [tool for tool in required if tool in used]
    missing = [tool for tool in required if tool not in used]
    forbidden_used = [tool for tool in case.forbidden_tools if tool in used]
    coverage = len(matched) / len(required) if required else 1.0
    # Attempting a forbidden tool is a hard governance miss, not a rounding error.
    score = coverage if not forbidden_used else max(0.0, coverage - 0.5)
    return MetricScore(
        name="tool_selection",
        score=score,
        detail={
            "used": sorted(used),
            "required": required,
            "matched": matched,
            "missing": missing,
            "forbidden_used": forbidden_used,
        },
    )


def score_evidence(result: RunResult, case: Case) -> MetricScore:
    corpus = evidence_corpus(result).lower()
    keywords = list(case.expected_keywords)
    matched = [kw for kw in keywords if kw.lower() in corpus]
    missing = [kw for kw in keywords if kw.lower() not in corpus]
    score = len(matched) / len(keywords) if keywords else 1.0
    return MetricScore(
        name="evidence",
        score=score,
        detail={
            "matched": matched,
            "missing": missing,
            "total": len(keywords),
            "corpus_chars": len(corpus),
        },
    )


def score_policy(result: RunResult) -> MetricScore:
    violations = blocked_tools(result)
    score = 0.0 if violations else 1.0
    return MetricScore(
        name="policy",
        score=score,
        detail={"violations": violations, "violation_count": len(violations)},
    )


def score_latency(result: RunResult, limits: ScoreLimits) -> MetricScore:
    seconds = result.latency_ms / 1000.0
    budget = limits.max_latency_s if limits.max_latency_s and limits.max_latency_s > 0 else 60.0
    score = max(0.0, min(1.0, 1.0 - seconds / budget))
    return MetricScore(
        name="latency",
        score=score,
        detail={"latency_ms": round(result.latency_ms, 2), "max_latency_s": budget},
    )


def score_cost(result: RunResult, limits: ScoreLimits) -> MetricScore:
    budget = limits.max_cost if limits.max_cost and limits.max_cost > 0 else 0.5
    score = max(0.0, min(1.0, 1.0 - result.cost / budget))
    return MetricScore(
        name="cost",
        score=score,
        detail={"cost": round(result.cost, 6), "max_cost": budget},
    )


def score_steps(result: RunResult, limits: ScoreLimits) -> MetricScore:
    budget = limits.max_steps if limits.max_steps and limits.max_steps > 0 else 16
    score = max(0.0, min(1.0, 1.0 - result.steps / budget))
    return MetricScore(
        name="steps",
        score=score,
        detail={"steps": result.steps, "max_steps": budget},
    )


# ---------------------------------------------------------------------------
# composition
# ---------------------------------------------------------------------------


def score_metrics(result: RunResult, limits: ScoreLimits | None = None) -> dict[str, MetricScore]:
    """Run every dimension scorer and store the results on *result*."""
    limits = limits or ScoreLimits()
    metrics = {
        "task_success": score_task_success(result, result.case),
        "tool_selection": score_tool_selection(result, result.case),
        "evidence": score_evidence(result, result.case),
        "policy": score_policy(result),
        "latency": score_latency(result, limits),
        "cost": score_cost(result, limits),
        "steps": score_steps(result, limits),
    }
    result.metrics = metrics
    return metrics


def overall_score(result: RunResult) -> float:
    """Mean of the seven dimension scores for a single case."""
    metrics = result.metrics or {}
    if not metrics:
        return 0.0
    return sum(m.score for m in metrics.values()) / len(metrics)


def aggregate(results: list[RunResult]) -> dict[str, Any]:
    """Mean score per dimension plus the mean overall across *results*."""
    if not results:
        return {}
    dimensions = DIMENSIONS
    scores: dict[str, list[float]] = {dim: [] for dim in dimensions}
    for result in results:
        for dim in dimensions:
            metric = result.metrics.get(dim)
            scores[dim].append(metric.score if metric is not None else 0.0)
    means = {dim: sum(values) / len(values) for dim, values in scores.items()}
    means["overall"] = sum(means.values()) / len(dimensions)
    return means


def aggregate_raw(results: list[RunResult]) -> dict[str, float]:
    """Mean raw latency / cost / steps across *results* (un-normalised)."""
    if not results:
        return {}
    n = len(results)
    return {
        "avg_latency_ms": round(sum(r.latency_ms for r in results) / n, 2),
        "avg_cost": round(sum(r.cost for r in results) / n, 6),
        "avg_steps": round(sum(r.steps for r in results) / n, 2),
        "completed": sum(1 for r in results if r.status == "completed"),
        "total": n,
    }
