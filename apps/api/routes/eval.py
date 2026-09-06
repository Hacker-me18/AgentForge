"""Evaluation endpoints: read real reports and re-run the offline harness.

Reports live under ``data/eval/`` and are produced by the offline evaluation
runner (deterministic mock). GETs serve the on-disk reports; POST ``/run``
re-executes the dataset and regenerates them — the numbers stay real because
the whole evaluation is deterministic.
"""

import json
import re
import time

from fastapi import APIRouter, HTTPException

from packages.evaluation.dataset import REPO_ROOT, Dataset
from packages.evaluation.experiment import run_ab
from packages.evaluation.runner import AgentSpec, EvaluationRunner

router = APIRouter(prefix="/api/eval", tags=["evaluation"])

REPORTS_DIR = REPO_ROOT / "data" / "eval"


def _fmt_created() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# single-dataset evaluation report
# ---------------------------------------------------------------------------


async def _run_eval_report() -> dict:
    dataset = Dataset.load_default()
    spec = AgentSpec(name="research-agent-v1.0", agent_id="research-agent", strategy="route")
    report = await EvaluationRunner().evaluate(dataset, spec)
    payload = report.to_dict()
    payload["created_at"] = _fmt_created()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "eval_report.md").write_text(report.markdown(), encoding="utf-8")
    (REPORTS_DIR / "eval_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


async def _eval_report() -> dict:
    path = REPORTS_DIR / "eval_report.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return await _run_eval_report()


# ---------------------------------------------------------------------------
# offline A/B experiment report
# ---------------------------------------------------------------------------

_FLOAT = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _pct(value: str) -> float:
    match = _FLOAT.search(value)
    return float(match.group(0)) / 100.0 if match else 0.0


def _parse_ab(markdown: str) -> dict:
    """Parse the markdown written by ``ABReport.markdown()`` back to JSON."""
    dataset = ""
    control = treatment = ""
    cases = 0
    improved = regressed = 0
    deltas: list[dict] = []
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("# A/B experiment:"):
            dataset = line.split(":", 1)[1].strip()
        elif "**Control**:" in line:
            control = line.split("`")[1] if "`" in line else ""
        elif "**Treatment**:" in line:
            treatment = line.split("`")[1] if "`" in line else ""
        elif "**Cases**:" in line:
            cases_match = _FLOAT.search(line)
            cases = int(cases_match.group(0)) if cases_match else 0
        elif "**Improved / regressed**:" in line:
            match = _FLOAT.findall(line)
            if len(match) >= 2:
                improved, regressed = int(match[0]), int(match[1])
        elif line.startswith("|") and "---" not in line:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 4 and cells[0] not in ("Dimension", ""):
                label, control_val, treatment_val = cells[0], cells[1], cells[2]
                c = _pct(control_val)
                t = _pct(treatment_val)
                deltas.append(
                    {
                        "dimension": label,
                        "control": round(c, 4),
                        "treatment": round(t, 4),
                        "delta": round(t - c, 4),
                    }
                )
    overall = round(sum(item["delta"] for item in deltas) / len(deltas) if deltas else 0.0, 4)
    return {
        "name": "ab_report",
        "kind": "ab",
        "dataset": dataset,
        "control": control,
        "treatment": treatment,
        "cases": cases,
        "overall_delta": overall,
        "improved": improved,
        "regressed": regressed,
        "deltas": deltas,
    }


async def _run_ab_report() -> dict:
    dataset = Dataset.load_default()
    control = AgentSpec(name="research-agent-v1.0", agent_id="research-agent", strategy="route")
    treatment = AgentSpec(name="research-agent-v1.1", agent_id="research-agent", strategy="echo")
    ab = await run_ab(dataset, control=control, treatment=treatment)
    markdown = ab.markdown()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "ab_report.md").write_text(markdown, encoding="utf-8")
    (REPORTS_DIR / "ab_report.json").write_text(
        json.dumps(ab.to_dict(), indent=2), encoding="utf-8"
    )
    payload = _parse_ab(markdown)
    payload["created_at"] = _fmt_created()
    return payload


async def _ab_report() -> dict:
    path = REPORTS_DIR / "ab_report.md"
    if path.exists():
        return _parse_ab(path.read_text(encoding="utf-8"))
    return await _run_ab_report()


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------


@router.get("/reports")
async def list_reports() -> list[dict]:
    return [
        {"id": "eval", "kind": "eval", "present": (REPORTS_DIR / "eval_report.json").exists()},
        {"id": "ab", "kind": "ab", "present": (REPORTS_DIR / "ab_report.md").exists()},
    ]


@router.get("/datasets/research")
async def research_dataset() -> dict:
    dataset = Dataset.load_default()
    payload = dataset.to_dict()
    payload["problems"] = dataset.validate_dataset()
    return payload


@router.get("/report/eval")
async def get_eval_report() -> dict:
    try:
        return await _eval_report()
    except Exception as exc:  # noqa: BLE001 - surface offline run failures clearly
        raise HTTPException(status_code=500, detail=f"evaluation failed: {exc}") from exc


@router.post("/report/eval/run")
async def rerun_eval_report() -> dict:
    try:
        return await _run_eval_report()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"evaluation failed: {exc}") from exc


@router.get("/report/ab")
async def get_ab_report() -> dict:
    try:
        return await _ab_report()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"experiment failed: {exc}") from exc


@router.post("/report/ab/run")
async def rerun_ab_report() -> dict:
    try:
        return await _run_ab_report()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"experiment failed: {exc}") from exc
