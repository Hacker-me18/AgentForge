"""Phase G tests: dataset integrity, evaluation runner, dimensions and A/B."""

from packages.evaluation.dataset import Case, Dataset
from packages.evaluation.experiment import run_ab
from packages.evaluation.metrics import DIMENSIONS, blocked_tools, used_tools
from packages.evaluation.runner import AgentSpec, EvaluationRunner

# ---------------------------------------------------------------------------
# 7.1 dataset / case models + >=30 research cases
# ---------------------------------------------------------------------------


def test_dataset_has_30_plus_research_cases() -> None:
    dataset = Dataset.load_default()
    assert len(dataset) >= 30
    ids = [case.id for case in dataset.cases]
    assert len(set(ids)) == len(ids)  # unique
    for case in dataset.cases:
        assert case.task
        assert case.expected_tools == ["web.search"]
        assert case.expected_keywords
        assert "shell.execute" in case.forbidden_tools


def test_dataset_validate_catches_duplicates() -> None:
    dataset = Dataset(
        name="bad",
        cases=[
            Case(id="a", task="t1", expected_tools=["web.search"], expected_keywords=["x"]),
            Case(id="a", task="t2", expected_tools=["web.search"], expected_keywords=["x"]),
        ],
    )
    problems = dataset.validate_dataset()
    assert any("duplicate case id" in p for p in problems)


def test_dataset_roundtrip_json(tmp_path) -> None:
    dataset = Dataset(
        name="tiny",
        cases=[Case(id="a", task="t1", expected_tools=["web.search"], expected_keywords=["x"])],
    )
    path = tmp_path / "tiny.json"
    dataset.to_json(path)
    loaded = Dataset.from_json(path)
    assert loaded.name == "tiny"
    assert loaded.cases[0].id == "a"


# ---------------------------------------------------------------------------
# 7.2 + 7.3 evaluation runner and the seven dimensions
# ---------------------------------------------------------------------------


async def test_evaluate_single_case_scores_well() -> None:
    case = Dataset.load_default().cases[0]
    result = await EvaluationRunner().run_case(case, AgentSpec(name="v1.0"))
    assert result.status == "completed"
    assert result.answer
    assert result.case.id == case.id
    assert set(result.metrics) == set(DIMENSIONS)

    assert result.metrics["task_success"].score == 1.0
    assert result.metrics["tool_selection"].score == 1.0
    assert result.metrics["evidence"].score == 1.0
    assert result.metrics["policy"].score == 1.0
    for metric in result.metrics.values():
        assert 0.0 <= metric.score <= 1.0
    # Trace was reconstructed from the collected events.
    assert result.trace["root"]["kind"] == "run"
    assert result.trace["root"]["status"] == "ok"


def test_feature_derivation_from_events() -> None:
    """used_tools / blocked_tools read the observation event payloads."""
    import asyncio

    case = Dataset.load_default().cases[0]
    runner = EvaluationRunner()
    result = asyncio.run(runner.run_case(case, AgentSpec(name="ok")))
    assert used_tools(result) == {"web.search"}
    assert blocked_tools(result) == []

    denied = asyncio.run(
        runner.run_case(
            case,
            AgentSpec(
                name="deny",
                policy_rules=[{"tool": "web.search", "action": "deny", "reason": "test"}],
            ),
        )
    )
    assert blocked_tools(denied) == [{"tool": "web.search", "error": "policy decision: deny"}]
    assert used_tools(denied) == set()


async def test_policy_violation_is_detected_and_costs_the_case() -> None:
    case = Dataset.load_default().cases[0]
    spec = AgentSpec(
        name="deny-search",
        policy_rules=[{"tool": "web.search", "action": "deny", "reason": "blocked"}],
    )
    result = await EvaluationRunner().run_case(case, spec)
    assert result.metrics["policy"].score == 0.0
    assert result.metrics["tool_selection"].score == 0.0
    assert result.metrics["evidence"].score == 0.0
    # It never actually executed the (denied) search, so it did not succeed.
    assert result.metrics["task_success"].score == 0.0


async def test_forbidden_tool_use_is_penalised() -> None:
    case = Case(
        id="guardrail",
        task="never use the echo tool",
        expected_tools=["web.search"],
        forbidden_tools=["mock.echo"],
        expected_keywords=["PostgreSQL"],
    )
    # echo strategy uses mock.echo, which this case forbids.
    result = await EvaluationRunner().run_case(case, AgentSpec(name="naive", strategy="echo"))
    assert "mock.echo" in result.metrics["tool_selection"].detail["forbidden_used"]
    assert result.metrics["tool_selection"].score < 1.0


async def test_evaluate_subset_returns_aggregate_report(tmp_path) -> None:
    dataset = Dataset.load_default()
    limited = Dataset(name="research", cases=dataset.cases[:4])
    report = await EvaluationRunner().evaluate(limited, AgentSpec(name="v1.0"))
    assert len(report.results) == 4
    aggregates = report.aggregates()
    assert set(DIMENSIONS) <= set(aggregates)
    assert aggregates["overall"] > 0.9
    assert report.raw()["completed"] == 4

    text = report.markdown()
    assert "# Evaluation report" in text
    assert "| Case |" in text
    assert all(case.id in text for case in limited.cases)

    payload = report.to_dict()
    assert payload["aggregates"]["task_success"] == 1.0


# ---------------------------------------------------------------------------
# 7.4 offline A/B experiment
# ---------------------------------------------------------------------------


async def test_ab_experiment_reports_control_vs_treatment() -> None:
    dataset = Dataset.load_default()
    limited = Dataset(name="research", cases=dataset.cases[:4])
    control = AgentSpec(name="v1.0", strategy="route")
    treatment = AgentSpec(name="v1.1", strategy="echo")
    report = await run_ab(limited, control=control, treatment=treatment)

    assert report.control.spec_name == "v1.0"
    assert report.treatment.spec_name == "v1.1"
    deltas = {d.dimension: d for d in report.dimension_deltas()}
    assert set(deltas) == set(DIMENSIONS)

    # The route agent searches and cites; the echo baseline does not.
    assert deltas["tool_selection"].treatment < deltas["tool_selection"].control
    assert deltas["evidence"].treatment < deltas["evidence"].control
    assert report.overall_delta() < 0.0
    assert report.per_case_overall()

    markdown = report.markdown()
    assert "A/B experiment" in markdown
    assert "v1.0" in markdown and "v1.1" in markdown
