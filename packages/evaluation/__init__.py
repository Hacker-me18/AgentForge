"""Evaluation: case datasets, per-case scoring, reports and offline A/B tests."""

from packages.evaluation.dataset import Case, Dataset
from packages.evaluation.experiment import ABReport, run_ab
from packages.evaluation.metrics import (
    DIMENSIONS,
    MetricScore,
    RunResult,
    ScoreLimits,
    aggregate,
    blocked_tools,
    evidence_corpus,
    overall_score,
    score_metrics,
    used_tools,
)
from packages.evaluation.report import EvaluationReport
from packages.evaluation.runner import AgentSpec, EvaluationRunner

__all__ = [
    "ABReport",
    "AgentSpec",
    "Case",
    "DIMENSIONS",
    "Dataset",
    "EvaluationReport",
    "EvaluationRunner",
    "MetricScore",
    "RunResult",
    "ScoreLimits",
    "aggregate",
    "blocked_tools",
    "evidence_corpus",
    "overall_score",
    "run_ab",
    "score_metrics",
    "used_tools",
]
