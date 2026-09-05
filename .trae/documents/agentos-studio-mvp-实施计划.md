# AgentOS Studio MVP 实施计划

## Summary

依据已批准的 spec（`.trae/specs/build-agentos-studio-mvp/`），按 Phase A~J 逐阶段构建 AgentOS Studio（Agent Runtime & Evaluation Platform）。**先完成环境准备（conda 环境由用户创建），再开始写代码**；每个 Phase 完成后运行测试验证、勾选 tasks.md / checklist.md 并汇报，再进入下一阶段，确保进度可追踪、不遗漏。

## Current State Analysis

已探明（2026-09-05）：

- 工作区 `d:\CodexProject\AgentForge`：git 仓库已初始化但**无提交**；仅 `docs/`（含设计施工方案）和 `.trae/specs/`（已批准的 spec/tasks/checklist）有内容
- `src/ configs/ scripts/ tests/ examples/ data/` 均为**空目录**（9 月 2 日创建，无代码）
- 工具链：
  - Anaconda 位于 `D:\software\Anaconda`（conda 25.11.1）；**系统 PATH 中的 `conda` 是失效占位符，必须用 `D:\software\Anaconda\Scripts\conda.exe` 全路径**
  - Python 3.13.9（base）、Node v22.23.2、Docker 28.5.1 均可用
  - 已有 conda 环境：base、agent、algorithm、coze、deeplearning、edu_agent、machine_learning、model、weather（**无 agentos**）
- 已批准 spec 三件套：`.trae/specs/build-agentos-studio-mvp/{spec,tasks,checklist}.md`

## 已确认决策

| 决策点 | 结论 |
|---|---|
| Conda 环境 | 新建 `agentos`，Python 3.11（与沙箱镜像 python:3.11 对齐），用户在终端执行创建命令 |
| 目录布局 | 按 docs 第 29 节 `apps/api` + `apps/web` + `packages/*` + `agents/*` monorepo；空目录 src/configs/scripts 删除，`data/` 保留作 SQLite 数据目录，`tests/` 保留 |
| 实施节奏 | 逐 Phase 推进，每阶段测试验证 + 勾选清单 + 汇报后进入下一阶段 |
| LLM 接入 | LLMProvider 接口 + LLMFactory（DeepSeek / OpenAI / OpenAI-compatible / Mock），默认 mock 可离线跑通 |

## Proposed Changes

### 第 0 步：环境准备（用户执行 + 我验证）

**先准备环境，不写任何业务代码。**

1. 我创建 `requirements.txt`（锁定核心依赖版本）和 `environment.yml`（可选便捷方式）：

```
# requirements.txt（核心，后续 Phase 按需追加）
fastapi>=0.115
uvicorn[standard]>=0.30
pydantic>=2.8
pydantic-settings>=2.4
sqlalchemy[asyncio]>=2.0
aiosqlite>=0.20
httpx>=0.27
pyyaml>=6.0
python-dotenv>=1.0
# dev
pytest>=8.0
pytest-asyncio>=0.23
ruff>=0.6
mypy>=1.11
pre-commit>=3.8
```

2. **用户在终端执行**（我提供命令，不代执行 conda 环境创建）：

```powershell
D:\software\Anaconda\Scripts\conda.exe create -n agentos python=3.11 -y
D:\software\Anaconda\Scripts\conda.exe run -n agentos pip install -r requirements.txt
D:\software\Anaconda\Scripts\conda.exe run -n agentos pip install -e .
```

3. 我验证：`conda run -n agentos python --version` 与 `pip list` 确认关键包就位。
4. 前端依赖（npm install）推迟到 Phase H 前；Docker 镜像 `python:3.11`（+pandas/numpy/matplotlib 定制镜像）在 Phase D 才构建。

### 第 1 步：Phase A — Monorepo 骨架（对应 tasks.md Task 1）

- 建目录：`apps/api`、`apps/web`、`packages/{runtime,context,memory,tools,sandbox,policy,tracing,evaluation,llm,adapters}`、`agents/{research,data_analyst}`、`datasets/`、`docker/`、`screenshots/`；删除空的 `src/ configs/ scripts/`
- `pyproject.toml`：setuptools，packages 可 `import packages.xxx`；ruff(line-length 100)/mypy(宽松)/pytest 配置
- `apps/api/`：`main.py`（FastAPI + `/health` + CORS）、`config.py`（pydantic-settings，llm_provider 默认 mock）、`db.py`（SQLAlchemy async + SQLite，落盘 `data/agentos.db`）、`logging_config.py`
- `apps/web/`：React18+TS+Vite+Tailwind v3 骨架；vite port 3000、proxy /api→8000；左侧深色导航（Overview/Agents/Runs/Traces/Tools/Sandbox/Policies/Evaluations/Experiments/Settings）+ react-router 占位页；**只写文件不 npm install**
- `.pre-commit-config.yaml`、`.gitignore`、`docs/adr/0001-architecture-decisions.md`
- `tests/test_health.py` 验证 /health
- **验证**：`conda run -n agentos python -m pytest tests/ -q` 通过；`ruff check` 通过 → 勾选 tasks.md Task 1

### 第 2 步：Phase B — Runtime 核心（Task 2）

- `packages/runtime/state.py`：AgentState（spec 全部字段）
- `packages/runtime/harness.py`：AgentHarness（prepare/build_context/resolve_tools/check_policy/execute/observe/finalize，不含业务逻辑）
- `packages/runtime/execution.py`：执行循环（max_steps/timeout/retry/cancellation/failure handling）
- `packages/runtime/checkpoint.py`：SQLite checkpoint + resume
- `packages/llm/`：`base.py`（LLMProvider.chat 接口）、`factory.py`（LLMFactory 按 LLM_PROVIDER 创建）、`providers/{mock,deepseek,openai_compatible}.py`
- `packages/context/`：Context Engine 管线（Collect→Rank→Compress→Budget→Assemble，token 预算与压缩）
- `packages/memory/`：短期/长期记忆（SQLite）
- **验证**：Mock LLM + Mock Tool 端到端测试；失败重试（Attempt1 FAILED→Attempt2 SUCCESS）；max_steps 超限 BUDGET_EXCEEDED → 勾选 Task 2

### 第 3 步：Phase C — Tool Registry / Gateway / MCP（Task 3）

- `packages/tools/registry.py`（元数据：name/description/schema/risk_level/timeout/cost/permission）、`gateway.py`（必经入口，Policy 检查后分发）
- `packages/tools/mcp/`：MCP Client + 示例 Server（calculator/search/filesystem/database，JSON-RPC over stdio 最小实现）
- **验证**：本地工具与 MCP 工具经 Gateway 调用成功 → 勾选 Task 3

### 第 4 步：Phase D — Docker Sandbox（Task 4）

- `packages/sandbox/`：SandboxRunner、DockerExecutor、ResourceLimits（network none、30s、512MB、1CPU、tmpfs）、ArtifactCollector
- `docker/sandbox.Dockerfile`：python:3.11 + pandas/numpy/matplotlib
- 接入 `python.execute` 工具
- **验证**：正常执行出 artifacts；timeout/内存/网络禁用/非法代码四类拦截测试 → 勾选 Task 4

### 第 5 步：Phase E — Policy 与审批（Task 5）

- `packages/policy/`：PolicyEngine（ALLOW/DENY/REQUIRE_APPROVAL + RiskLevel）、Budget（max_steps/max_tokens/max_cost/max_latency）
- Approval 模型 + API（创建/Approve/Reject/审计），Runtime 暂停-恢复
- **验证**：三种动作路径 + database.write 审批流测试 → 勾选 Task 5

### 第 6 步：Phase F — Event / Trace / Cost（Task 6）

- `packages/tracing/`：Event 模型（id/run_id/type/timestamp/sequence/payload）、EventBus、EventStore（SQLite）、TraceBuilder（Span 树）、CostTracker（模型价格表）
- Runtime/Gateway/Sandbox 埋点，不侵入业务代码
- API：`/api/runs`、`/api/runs/{id}/trace`、`/api/events`
- **验证**：完整 Run 产生完整 Trace Tree 与成本汇总 → 勾选 Task 6

### 第 7 步：Phase G — Evaluation 与 A/B（Task 7）

- `packages/evaluation/`：Dataset/Case/Runner/Evaluator/Metrics/Report；维度：Task Success/Tool Selection/Evidence/Policy/Latency/Cost/Steps
- `datasets/research-v1.jsonl`：≥30 条用例
- 离线 A/B Experiment（Control vs Treatment）
- **验证**：评估独立运行输出真实对比报告 → 勾选 Task 7

### 第 8 步：Phase H — Web UI（Task 8）

- `npm install`（此时才装前端依赖）
- Overview（真实指标卡+Recent Runs）、Agents 详情（Run/Evaluate/View Trace/Edit）、**Traces 页面（最高优先级：时间线+Span 详情）**、Runs/Tools/Sandbox/Policies/Evaluations/Experiments、Approval 弹窗
- **验证**：`npm run build` 通过；全页面对接真实 API → 勾选 Task 8

### 第 9 步：Phase I — Demo Agents（Task 9）

- `agents/research/`：web.search+document.read+python.execute，含证据报告
- `agents/data_analyst/`：CSV 上传→沙箱 Pandas→图表 artifact→结论
- 种子数据脚本（research-agent v1.0/v1.1、prompt v1~v3、policy 表）
- **验证**：两个 Demo 端到端 Trace 符合预期 → 勾选 Task 9

### 第 10 步：Phase J — 交付打磨（Task 10）

- `docker-compose.yml`（api+web）、`docker/api.Dockerfile`、`docker/web.Dockerfile`
- README（Hero 架构图、Demo GIF、Feature cards、截图、Quick Start、Architecture、Roadmap）、≥3 张架构图（drawio/mermaid 导出 png 至 docs/images/）
- 真实运行数据替换所有示例数字
- **验证**：`docker compose up` 一键起，localhost:3000 跑通 Research Agent 全链路 → 勾选 Task 10

## 进度记忆机制（防遗漏）

1. `.trae/specs/build-agentos-studio-mvp/tasks.md`：每完成一个 Task/SubTask 立即勾选 `- [x]`
2. `.trae/specs/build-agentos-studio-mvp/checklist.md`：每 Phase 验证后勾选
3. 每 Phase 结束我口头汇报：已完成项 / 测试结果 / 下一阶段前置条件
4. 每个 Phase 完成后做一次 git commit（feat: phase X ...），形成可回滚节点

## Assumptions & Decisions

- 沙箱镜像基于 `python:3.11-slim` + pandas/numpy/matplotlib，Phase D 构建（需联网拉镜像）
- 默认 LLM_PROVIDER=mock，真实 Key（DeepSeek/OpenAI）由用户后续在 `.env` 配置，非 MVP 阻塞项
- npm install 与 Docker 镜像构建需要网络；若失败则降级：Docker 不可用时 Sandbox 用本地子进程 + 资源限制模拟（仅在用户同意后降级，优先真实 Docker）
- MCP 采用最小 JSON-RPC stdio 实现，不引入官方 SDK 重依赖（保持轻量；如官方 mcp 包稳定可直接用，Phase C 时定）
- 空目录 src/configs/scripts 删除；data/ 保留存 SQLite 与 artifacts

## Verification

每 Phase 关卡（Gate）：

| Phase | 验证命令 / 标准 |
|---|---|
| 0 | `conda run -n agentos python --version` = 3.11.x；关键包可 import |
| A | `pytest tests/ -q` 全绿；`ruff check .` 无错 |
| B | runtime 单测全绿（mock 端到端 / 重试 / 预算停止 / checkpoint resume） |
| C | Gateway+MCP 调用测试全绿 |
| D | sandbox 四类限制测试全绿（需 Docker 运行中） |
| E | policy 三路径 + 审批流测试全绿 |
| F | 完整 Run 的 Trace Tree/成本汇总断言通过 |
| G | 评估 Runner 输出真实报告；A/B 对比表生成 |
| H | `npm run build` 通过；UI 数据与 API 一致 |
| I | 两个 Demo 端到端 Trace 断言通过 |
| J | `docker compose up` 后 localhost:3000 全链路验收（checklist.md 最终场景） |

全部 Phase 完成后，逐条核对 `checklist.md` 并全部勾选，发布 v0.1.0。
