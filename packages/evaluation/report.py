"""Aggregated evaluation report and its markdown/JSON rendering."""

import time
from dataclasses import dataclass, field
from typing import Any

from packages.evaluation.metrics import (
    DIMENSION_LABELS,
    DIMENSIONS,
    RunResult,
    aggregate,
    aggregate_raw,
    overall_score,
)

DIM_LABEL = DIMENSION_LABELS


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _score_row(result: RunResult) -> dict[str, Any]:
    row: dict[str, Any] = {"case_id": result.case.id, "status": result.status}
    for dim in DIMENSIONS:
        metric = result.metrics.get(dim)
        row[dim] = metric.score if metric is not None else 0.0
    row["overall"] = overall_score(result)
    # Raw values use underscored keys so they never collide with score columns.
    row["raw_latency_ms"] = round(result.latency_ms, 2)
    row["raw_cost"] = result.cost
    row["raw_steps"] = result.steps
    return row


@dataclass
class EvaluationReport:
    dataset_name: str
    spec_name: str
    results: list[RunResult] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def aggregates(self) -> dict[str, float]:
        return aggregate(self.results)

    def raw(self) -> dict[str, Any]:
        return aggregate_raw(self.results)

    def rows(self) -> list[dict[str, Any]]:
        return [_score_row(result) for result in self.results]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset_name,
            "spec": self.spec_name,
            "case_count": len(self.results),
            "aggregates": self.aggregates(),
            "raw": self.raw(),
            "results": self.rows(),
        }

    # -- rendering ---------------------------------------------------------

    def markdown(self) -> str:
        lines = [
            f"# Evaluation report: {self.dataset_name}",
            "",
            f"- **Agent spec**: `{self.spec_name}`  ",
            f"- **Cases**: {len(self.results)}",
        ]
        aggregates = self.aggregates()
        raw = self.raw()
        lines.append(f"- **Overall**: {_pct(aggregates['overall'])}")
        lines.extend(self._dimension_lines(aggregates))
        lines.extend(
            [
                "",
                f"- Avg latency **{raw['avg_latency_ms']} ms** · Avg cost "
                f"**${raw['avg_cost']:.6f}** · Avg steps **{raw['avg_steps']}** · "
                f"Completed **{raw['completed']}/{raw['total']}**",
                "",
                "| Case | Status | "
                + " | ".join(DIM_LABEL[d] for d in DIMENSIONS)
                + " | Overall |",
                "| --- | --- |" + " --- |" * (len(DIMENSIONS) + 1),
            ]
        )
        for row in self.rows():
            cells = [row["case_id"], row["status"]]
            cells += [_pct(row[dim]) for dim in DIMENSIONS]
            cells.append(_pct(row["overall"]))
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
        return "\n".join(lines)

    def _dimension_lines(self, aggregates: dict[str, float]) -> list[str]:
        return [f"- **{DIM_LABEL[dim]}**: {_pct(aggregates[dim])}" for dim in DIMENSIONS]
