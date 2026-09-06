"""Offline A/B experiments: Control vs Treatment over the same dataset.

The whole dataset is executed once per arm and the seven evaluation
dimensions are compared arm-over-arm. A positive ``delta`` always means the
treatment improved on that dimension.

Usage::

    report = await run_ab(
        dataset,
        control=AgentSpec(name="v1.0", strategy="route"),
        treatment=AgentSpec(name="v1.1", strategy="echo"),
    )
    print(report.markdown())
"""

from dataclasses import dataclass
from typing import Any

from packages.evaluation.dataset import Dataset
from packages.evaluation.metrics import DIMENSIONS, overall_score
from packages.evaluation.report import EvaluationReport
from packages.evaluation.runner import AgentSpec, EvaluationRunner
from packages.llm.base import LLMProvider


@dataclass
class DimensionDelta:
    dimension: str
    control: float
    treatment: float
    delta: float


@dataclass
class ABReport:
    dataset_name: str
    control: EvaluationReport
    treatment: EvaluationReport

    # -- computation ------------------------------------------------------

    def _agg(self, report: EvaluationReport) -> dict[str, float]:
        return report.aggregates()

    def dimension_deltas(self) -> list[DimensionDelta]:
        control = self._agg(self.control)
        treatment = self._agg(self.treatment)
        return [
            DimensionDelta(
                dimension=dim,
                control=control[dim],
                treatment=treatment[dim],
                delta=treatment[dim] - control[dim],
            )
            for dim in DIMENSIONS
        ]

    def overall_delta(self) -> float:
        return self._agg(self.treatment)["overall"] - self._agg(self.control)["overall"]

    def per_case_overall(self) -> dict[str, float]:
        control = {r.case.id: overall_score(r) for r in self.control.results}
        treatment = {r.case.id: overall_score(r) for r in self.treatment.results}
        return {
            case_id: treatment.get(case_id, 0.0) - control.get(case_id, 0.0)
            for case_id in sorted(set(control) | set(treatment))
        }

    # -- rendering --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset_name,
            "control": self.control.spec_name,
            "treatment": self.treatment.spec_name,
            "deltas": [
                {
                    "dimension": d.dimension,
                    "control": round(d.control, 4),
                    "treatment": round(d.treatment, 4),
                    "delta": round(d.delta, 4),
                }
                for d in self.dimension_deltas()
            ],
            "overall_delta": round(self.overall_delta(), 4),
            "per_case_delta": {k: round(v, 4) for k, v in self.per_case_overall().items()},
        }

    def markdown(self) -> str:
        deltas = self.dimension_deltas()
        per_case = self.per_case_overall()
        improved = sum(1 for value in per_case.values() if value > 0.001)
        regressed = sum(1 for value in per_case.values() if value < -0.001)

        def _fmt(value: float) -> str:
            arrow = "▲" if value > 0.001 else ("▼" if value < -0.001 else "·")
            return f"{value * 100:+.1f}% {arrow}"

        lines = [
            f"# A/B experiment: {self.dataset_name}",
            "",
            f"- **Control**: `{self.control.spec_name}`  ",
            f"- **Treatment**: `{self.treatment.spec_name}`  ",
            f"- **Cases**: {len(self.control.results)}  ",
            f"- **Overall delta**: {_fmt(self.overall_delta())}  ",
            f"- **Improved / regressed**: {improved} / {regressed} case(s)",
            "",
            "| Dimension | Control | Treatment | Δ |",
            "| --- | --- | --- | --- |",
        ]
        for dim in deltas:
            label = {
                "task_success": "Task Success",
                "tool_selection": "Tool Selection",
                "evidence": "Evidence",
                "policy": "Policy",
                "latency": "Latency",
                "cost": "Cost",
                "steps": "Steps",
            }[dim.dimension]
            lines.append(
                f"| {label} | {dim.control * 100:.1f}% | "
                f"{dim.treatment * 100:.1f}% | {_fmt(dim.delta)} |"
            )
        lines.append("")
        return "\n".join(lines)


async def run_ab(
    dataset: Dataset,
    control: AgentSpec,
    treatment: AgentSpec,
    llm: LLMProvider | None = None,
    runner: EvaluationRunner | None = None,
) -> ABReport:
    """Run *dataset* under both specs and return their comparison report."""
    runner = runner or EvaluationRunner(llm=llm)
    control_report = await runner.evaluate(dataset, control)
    treatment_report = await runner.evaluate(dataset, treatment)
    return ABReport(dataset_name=dataset.name, control=control_report, treatment=treatment_report)
