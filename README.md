<p align="center">
  <img src="screenshots/overview.png" alt="AgentOS Studio overview" width="880" />
</p>

<h1 align="center">AgentOS Studio</h1>

<p align="center">
  An open-source agent runtime, governance and evaluation platform.<br/>
  Python backend · React web console · swappable LLM providers (offline by default).
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-blue" alt="python 3.11"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"/>
</p>

---

## Overview

AgentOS Studio is the infrastructure for running agents that use tools under
governance, with full observability and reproducible offline evaluation. It is
structured as a set of independently usable `packages/*` modules composed by a
FastAPI service and by the offline evaluation runner:

- **Agent runtime** — a checkpointed execution loop (`packages/runtime`): the
  agent chats, plans tool calls, pauses for approval, and saves a checkpoint
  after every step.
- **Tool gateway** — every tool call goes through `ToolGateway` and a policy
  check *before* it executes (`packages/tools`, `packages/policy`). A governed
  tool such as `database.write` pauses the whole run until a person approves or
  rejects it.
- **Docker sandbox** — `python.execute` runs code in an isolated container with
  no network and memory/CPU limits (`packages/sandbox`).
- **Tracing** — the runtime emits ordered lifecycle events; traces, cost and
  audit records are derived from that stream (`packages/tracing`).
- **Evaluation** — an offline runner scores agents on a 31-case dataset across
  7 dimensions, and an A/B runner compares whole agents
  (`packages/evaluation`).

The web console (`apps/web`) is the UI over the API (`apps/api`): 10 screens —
Overview, Agents, Runs, Traces, Tools, Policies, Sandbox, Evaluations,
Experiments, Settings — including a live run viewer and the approval inbox.

Running the project requires no API keys. The default `mock` LLM provider is
deterministic, so the evaluation and A/B reports are reproducible; swap in a
real provider (DeepSeek or OpenAI-compatible) via `.env` and the same harness
scores real runs.

## Screenshots

Screenshots are captured from the seeded example data (see below).

| Overview | Runs | Traces |
|:---|:---|:---|
| ![overview](screenshots/overview.png) | ![runs](screenshots/runs.png) | ![traces](screenshots/traces.png) |

| Run detail | Human approval | Tools |
|:---|:---|:---|
| ![run-detail](screenshots/run-detail.png) | ![waiting-approval](screenshots/waiting-approval.png) | ![tools](screenshots/tools.png) |

| Sandbox | Evaluations | Experiments |
|:---|:---|:---|
| ![sandbox](screenshots/sandbox.png) | ![evaluations](screenshots/evaluations.png) | ![experiments](screenshots/experiments.png) |

## Example data

`python scripts/seed_demo.py` clears the local database and runs a fixed set of
tasks through the same stack the API uses — nothing in the UI below is
hand-inserted except the human decision on the one approval. After seeding:

| Metric | Value |
|---|---:|
| Runs | 9 of 9 completed |
| Tool calls | `web.search` ×6 · `calculator` ×2 · `database.write` ×2 |
| Token usage | 12,657 (12,058 in / 599 out) · est. $0.0039 at DeepSeek pricing |
| Agents | 4 — Research, Data Analyst, Data Writer, Default |
| Policy rules | 8 — 6 `allow` · 1 `deny` · 1 `require_approval` |
| Human approval | 1 — the Data Writer's ledger write requires approval |
| Evaluation | 31 cases → overall 0.9821, all 7 dimensions ≥ 0.875 |
| A/B experiment | `research-agent-v1.0` vs `v1.1` → control wins 31/31 (Δ −0.3597) |

Because the default LLM is deterministic, re-running the eval / A/B report
endpoints reproduces the same numbers.

## Getting started

### Run locally

Backend (Python ≥ 3.11):

```bash
pip install -e ".[dev]"
python scripts/seed_demo.py       # create data/agentos.db with the example runs
uvicorn apps.api.main:app --port 8000
```

API on http://localhost:8000 — interactive docs at `/docs`, health at `/health`.

Frontend (Node ≥ 18):

```bash
cd apps/web
npm install
npm run dev                        # console on http://localhost:3000
```

From the console you can launch the seeded agents' one-click tasks, watch a
Data Writer run pause for approval and approve it, run Python in the Sandbox
page, and re-run the evaluation or the A/B experiment.

### Docker

```bash
docker compose build && docker compose up     # web :3000 · api :8000
docker compose --profile build build sandbox  # optional: python.execute image
```

The sandbox runs code through a container built from `docker/sandbox.Dockerfile`
(`agentos-sandbox:0.1`). It is only needed when you actually execute code in
the sandbox or via `python.execute`; the seeded demo and the other pages never
use it. The API must have access to the local Docker daemon for it to work.

### Use a real LLM

Create `.env` next to `pyproject.toml` (values are read with the `AGENTOS_`
prefix):

```bash
AGENTOS_LLM_PROVIDER=deepseek            # mock | deepseek | openai | openai_compatible
AGENTOS_LLM_MODEL=deepseek-chat
AGENTOS_DEEPSEEK_API_KEY=sk-...          # or AGENTOS_OPENAI_API_KEY and AGENTOS_OPENAI_BASE_URL
```

With `mock` (the default) nothing else is needed. Cost and token figures in the
dashboards are computed from the provider's pricing model.

## Packages

| Package | Purpose |
|---|---|
| `packages/runtime` | `AgentState`, `AgentHarness`, `AgentRuntime`, `ContextEngine`, `Checkpoint`, `Budget` |
| `packages/tools` | `ToolRegistry`, `ToolGateway`, builtin tools, MCP client/server |
| `packages/policy` | `PolicyEngine` (allow / deny / require_approval), `ApprovalManager` |
| `packages/sandbox` | Docker executor with resource limits and artifact collection |
| `packages/llm` | Provider factory — `mock` (deterministic, offline), `deepseek`, `openai_compatible` |
| `packages/tracing` | `EventBus`, `EventStore`, `TraceBuilder` |
| `packages/evaluation` | Offline `EvaluationRunner`, 31-case dataset, A/B comparator |

Architecture diagrams (system context, run lifecycle, governance/approval flow,
event→trace pipeline, evaluation runner) are in [`docs/architecture.md`](docs/architecture.md).

## Quality checks

```bash
ruff check .        # lint
mypy packages apps agents tests    # types
pytest -q           # tests
```

Tests cover the runtime loop, the gateway envelope and policy enforcement, the
approval pause/resume path, sandbox execution, event-bus ordering, and an
end-to-end run over the HTTP API.

## Repository layout

```
apps/api         FastAPI service: routers, run_service, SQLite store
apps/web         React 18 + TypeScript + Tailwind console (10 screens)
agents           agent definitions and one-click demo tasks
packages/        platform modules (runtime, tools, policy, llm, tracing, evaluation, sandbox)
scripts/seed_demo.py    deterministic example dataset (9 runs)
datasets/        sample documents + evaluation case set
docs/            architecture diagrams, ADR
screenshots/     UI screenshots used in this README
docker/          sandbox Dockerfile
```

## License

[MIT](LICENSE) © 2026 贺朝晖 (Hacker-me18)

中文文档见 [docs/README.zh-CN.md](docs/README.zh-CN.md)。
