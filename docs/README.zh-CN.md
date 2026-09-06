# AgentForge Studio(中文)

> English: [`README.md`](../README.md)

AgentForge Studio 是一个开源的 Agent 运行时、治理与评测平台。Python 后端、React Web 控制台,LLM 提供方可切换(默认完全离线)。

## 概述

AgentForge Studio 提供「让 Agent 用工具、受治理、可观测、可评测」所需的基础设施,并按可独立复用的 `packages/*` 模块组织,由 FastAPI 服务与离线评测运行器组合使用:

- **Agent 运行时**(`packages/runtime`):带 checkpoint 的执行循环——对话、规划工具调用、审批暂停、每步保存状态。
- **工具网关**(`packages/tools`、`packages/policy`):每次工具调用先经过 `ToolGateway` 与策略检查再执行。受治理的工具(如 `database.write`)会让整个运行**暂停**,直到有人在界面里批准或拒绝。
- **Docker 沙箱**(`packages/sandbox`):`python.execute` 在隔离容器中运行代码,禁网、限制内存/CPU。
- **追踪**(`packages/tracing`):运行时产生有序生命周期事件;trace、成本、审计记录都由事件流派生。
- **评测**(`packages/evaluation`):离线运行器在 31 个 case 的评测集上按 7 个维度打分;A/B 运行器对整组 Agent 做对比。

Web 控制台(`apps/web`)是 API(`apps/api`)之上的界面,共 10 个页面:Overview、Agents、Runs、Traces、Tools、Policies、Sandbox、Evaluations、Experiments、Settings,含实时运行的查看器与审批收件箱。

项目运行**不需要任何 API Key**。默认的 `mock` LLM 是确定性的,因此评测与 A/B 报告可复现;在 `.env` 里换成真实提供方(DeepSeek 或 OpenAI 兼容)后,同一套 harness 会对真实运行打分。

## 界面截图

截图取自下面的种子示例数据。

| 总览 | 运行 | 追踪 |
|:---|:---|:---|
| ![overview](../screenshots/overview.png) | ![runs](../screenshots/runs.png) | ![traces](../screenshots/traces.png) |

| 运行详情 | 人工审批 | 工具 |
|:---|:---|:---|
| ![run-detail](../screenshots/run-detail.png) | ![waiting-approval](../screenshots/waiting-approval.png) | ![tools](../screenshots/tools.png) |

| 沙箱 | 评测 | 实验 |
|:---|:---|:---|
| ![sandbox](../screenshots/sandbox.png) | ![evaluations](../screenshots/evaluations.png) | ![experiments](../screenshots/experiments.png) |

## 示例数据

`python scripts/seed_demo.py` 会重建本地数据库,并让一组固定任务走一遍与 API 完全相同的链路——界面里的数据都是真实运行产生的,只有那一次人工审批是手动点的。种子结果:

| 指标 | 数值 |
|---|---:|
| 运行 | 9 / 9 完成 |
| 工具调用 | `web.search` ×6 · `calculator` ×2 · `database.write` ×2 |
| Token 用量 | 12,657(输入 12,058 / 输出 599)· 按 DeepSeek 计价约 $0.0039 |
| Agent | 4 — 研究、数据分析、数据写入、默认 |
| 策略规则 | 8 — 6 `allow` · 1 `deny` · 1 `require_approval` |
| 人工审批 | 1 次 — Data Writer 的账本写入需批准 |
| 评测 | 31 个 case → 总体 0.9821,7 个维度均 ≥ 0.875 |
| A/B 实验 | `research-agent-v1.0` vs `v1.1` → 对照组胜 31/31(Δ −0.3597) |

默认 LLM 是确定性的,所以重跑评测 / A/B 报告接口会得到相同的数字。

## 快速开始

**后端**(Python ≥ 3.11):

```bash
pip install -e ".[dev]"
python scripts/seed_demo.py       # 生成 data/agentos.db(示例运行)
uvicorn apps.api.main:app --port 8000
```

API 位于 http://localhost:8000,交互文档 `/docs`,健康检查 `/health`。

**前端**(Node ≥ 18):

```bash
cd apps/web
npm install
npm run dev                        # 控制台 → http://localhost:3000
```

在控制台里可以:运行种子 Agent 的一键任务、观察 Data Writer 暂停等待审批并批准、在沙箱页执行 Python、重跑评测或 A/B 实验。

### Docker

```bash
docker compose build && docker compose up     # web :3000 · api :8000
docker compose --profile build build sandbox  # 可选:python.execute 镜像
```

沙箱通过 `docker/sandbox.Dockerfile` 构建的 `agentos-sandbox:0.1` 容器执行代码。只有真正在沙箱页或通过 `python.execute` 执行代码时才需要它,种子演示和其它页面都用不到;并且 API 需要能访问本机 Docker 才能工作。

### 接入真实 LLM

在项目根目录创建 `.env`(变量带 `AGENTOS_` 前缀):

```bash
AGENTOS_LLM_PROVIDER=deepseek            # mock | deepseek | openai | openai_compatible
AGENTOS_LLM_MODEL=deepseek-chat
AGENTOS_DEEPSEEK_API_KEY=sk-...          # 或 AGENTOS_OPENAI_API_KEY 与 AGENTOS_OPENAI_BASE_URL
```

默认 `mock` 不需要配置。仪表盘里的成本与 token 数据按对应模型的计价计算。

## 包结构

| 包 | 作用 |
|---|---|
| `packages/runtime` | `AgentState`、`AgentHarness`、`AgentRuntime`、`ContextEngine`、`Checkpoint`、`Budget` |
| `packages/tools` | `ToolRegistry`、`ToolGateway`、内置工具、MCP 客户端/服务端 |
| `packages/policy` | `PolicyEngine`(allow / deny / require_approval)、`ApprovalManager` |
| `packages/sandbox` | Docker 执行器(资源限制 + 产物收集) |
| `packages/llm` | 提供方工厂 —— `mock`(确定性、离线)、`deepseek`、`openai_compatible` |
| `packages/tracing` | `EventBus`、`EventStore`、`TraceBuilder` |
| `packages/evaluation` | 离线 `EvaluationRunner`、31-case 数据集、A/B 比较 |

架构图(系统上下文、运行生命周期、治理/审批流程、事件→追踪、评测流水线)见 [`docs/architecture.md`](architecture.md)。

## 质量检查

```bash
ruff check .        # lint
mypy packages apps agents tests    # 类型
pytest -q           # 测试
```

测试覆盖运行时循环、网关信封与策略执行、审批暂停/恢复、沙箱执行、事件总线顺序,以及一次走 HTTP API 的端到端运行。

## 目录结构

```
apps/api         FastAPI 服务:路由、run_service、SQLite 存储
apps/web         React 18 + TypeScript + Tailwind 控制台(10 屏)
agents           Agent 定义与一键演示任务
packages/        平台模块(runtime、tools、policy、llm、tracing、evaluation、sandbox)
scripts/seed_demo.py    确定性示例数据集(9 次运行)
datasets/        示例文档 + 评测用例集
docs/            架构图、ADR
screenshots/     本 README 使用的界面截图
docker/          沙箱 Dockerfile
```

## License

[MIT](../LICENSE) © 2026 hzh
