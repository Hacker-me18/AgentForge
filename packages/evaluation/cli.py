"""Standalone evaluation entry point (runs without a server).

Runs the research dataset offline with a deterministic mock LLM by default,
prints a markdown report and optionally writes it to ``data/eval/``. With
``--live`` the configured real LLM provider (AGENTOS_LLM_PROVIDER=deepseek/...)
is used instead, which makes Evidence/Policy scoring meaningful end to end.

Examples::

    python -m packages.evaluation.cli                       # mock, default dataset
    python -m packages.evaluation.cli --ab                  # control vs treatment
    python -m packages.evaluation.cli --limit 8 --out data/eval_report.md
"""

import argparse
import asyncio
from pathlib import Path

from packages.evaluation.dataset import DEFAULT_DATASET_PATH, Dataset
from packages.evaluation.experiment import run_ab
from packages.evaluation.runner import AgentSpec, EvaluationRunner
from packages.llm.base import LLMProvider


def _build_spec(name: str, strategy: str, args: argparse.Namespace) -> AgentSpec:
    return AgentSpec(
        name=name,
        strategy=strategy,
        system_prompt=args.system_prompt,
        max_steps=args.max_steps,
    )


def _live_llm() -> LLMProvider | None:
    from apps.api.config import settings  # lazy: requires the API settings env
    from packages.llm.factory import LLMFactory

    return LLMFactory.create(settings)


async def _run(args: argparse.Namespace) -> None:
    dataset = Dataset.from_json(args.dataset)
    problems = dataset.validate_dataset()
    if problems:
        raise SystemExit(f"dataset invalid: {problems}")

    live = args.live
    llm = _live_llm() if live else None
    runner = EvaluationRunner(llm=llm)

    out_dir = args.out_dir
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)

    cases = dataset.cases if args.limit is None else dataset.cases[: args.limit]
    limited = Dataset(name=dataset.name, description=dataset.description, cases=cases)

    if args.ab:
        control = _build_spec(args.control_name, args.control_strategy, args)
        treatment = _build_spec(args.treatment_name, args.treatment_strategy, args)
        ab_report = await run_ab(
            limited, control=control, treatment=treatment, llm=llm, runner=runner
        )
        text = ab_report.markdown()
        print(text)
        if out_dir:
            path = Path(out_dir) / "ab_report.md"
            path.write_text(text, encoding="utf-8")
            print(f"\nA/B report written to {path}")
    else:
        spec = _build_spec(args.agent_name, args.strategy, args)
        eval_report = await runner.evaluate(limited, spec)
        text = eval_report.markdown()
        print(text)
        if out_dir:
            path = Path(out_dir) / "eval_report.md"
            path.write_text(text, encoding="utf-8")
            import json

            (Path(out_dir) / "eval_report.json").write_text(
                json.dumps(eval_report.to_dict(), indent=2), encoding="utf-8"
            )
            print(f"\nReports written to {path} and .json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--limit", type=int, default=None, help="first N cases only")
    parser.add_argument("--strategy", default="route", choices=["route", "echo"])
    parser.add_argument("--agent-name", default="research-agent-v1.0")
    parser.add_argument("--max-steps", type=int, default=16)
    parser.add_argument("--system-prompt", default=None)
    parser.add_argument("--ab", action="store_true", help="run an A/B experiment")
    parser.add_argument("--control-name", default="research-agent-v1.0")
    parser.add_argument("--control-strategy", default="route", choices=["route", "echo"])
    parser.add_argument("--treatment-name", default="research-agent-v1.1")
    parser.add_argument("--treatment-strategy", default="echo", choices=["route", "echo"])
    parser.add_argument("--live", action="store_true", help="use the configured real LLM")
    parser.add_argument(
        "--out-dir", default="data/eval", help="directory to write markdown reports"
    )
    args = parser.parse_args(argv)
    asyncio.run(_run(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
