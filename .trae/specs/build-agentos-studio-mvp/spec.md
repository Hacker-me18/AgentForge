# AgentOS Studio MVP Spec

## Why

依据 `docs/AgentOS_Studio_GitHub展示项目_设计施工方案.md`，项目目标不是再做一个业务 Agent，而是构建一个开源的 **Agent Infrastructure / AgentOps 平台**（AgentOS Studio），让 Agent 从"能调用 LLM"变成"可运行、可观察、可评估、可治理"（Build / Run / Trace / Evaluate / Govern），并作为 GitHub 展示作品提供完整 Demo、架构图、截图与一键 Docker Compose 体验。

## What Changes

- 新建 monorepo 工程骨架：`apps/api`（FastAPI 后端）、`apps/web`（React + TS + Vite + TailwindCSS）、`packages/*`（runtime、context、memory、tools、sandbox、policy、tracing、evaluation、llm、adapters）、`agents/*`（research、data_analyst）
- Control Plane：Agent Registry（创建/版本/发布/回滚/归档）、Prompt Registry（版本/Diff/评估分）、Tool Registry、Policy、Evaluation、Experiments
- Data Plane：AgentHarness + AgentRuntime 执行循环（max_steps / timeout / retry / cancellation / checkpoint / resume / failure handling）、统一 AgentState、Context Engine（Collect→Rank→Compress→Budget→Assemble，含 token 预算与压缩）、Short/Long-term Memory（SQLite）
- LLM 接入采用 **LLMProvider Adapter + LLMFactory**：工厂按配置创建 DeepSeek / OpenAI / OpenAI-compatible / Mock provider，默认 provider 由环境变量决定，Mock 保证离线可跑通
- Tool Gateway：所有工具调用必经 Gateway（注册元数据：name/schema/risk_level/timeout/cost/permission），MCP Client/Server 作为工具集成协议接入（search/filesystem/database/calculator），不强制全量 MCP 化
- Docker Sandbox：`python.execute` 在 Docker 中运行（network disabled、timeout 30s、512MB 内存、1 CPU、临时文件系统），支持 pandas/numpy/matplotlib，返回 artifacts
- Policy Engine：ALLOW / DENY / REQUIRE_APPROVAL；高风险工具（如 database.write）触发 Human-in-the-loop 审批 UI
- Budget Control：max_steps / max_tokens / max_cost / max_latency，超限即 STOP
- Event / Trace / Cost / Audit：统一 Event 模型（run.started、llm.request、tool.request、policy.checked、sandbox.completed 等），Trace Tree 展示 Latency/Tokens/Cost，Trace 不侵入业务代码
- Evaluation：Dataset（约 30 cases）→ Runner → Evaluator → Score → Report，评价维度含 Task Success / Tool Selection / Evidence / Policy / Latency / Cost / Steps；支持离线 A/B 实验（Control vs Treatment）
- Web UI（Agent Engineer Console 风格）：Overview / Agents / Runs / Traces（最重要）/ Tools / Sandbox / Policies / Evaluations / Experiments / Settings
- Demo Agents：Research Agent（PostgreSQL vs MySQL 对比研究）、Data Analyst Agent（CSV 上传 + Pandas 分析出图）
- 交付物：README（Hero 架构图 + Demo GIF + Feature cards + 截图 + Quick Start）、≥3 张架构图、docker-compose 一键启动、pytest/ruff/mypy/pre-commit 工程链
- 明确不引入：Kubernetes、Kafka、Redis Cluster、PostgreSQL 集群、Firecracker/MicroVM、Service Mesh、Ray 等

## Impact

- Affected specs: 本 change 为项目首个 spec，定义全部 MVP 能力基线
- Affected code: 全新代码库 `d:\CodexProject\AgentForge`（monorepo）
- 外部依赖：Docker（Sandbox 与 compose）、LLM API Key（DeepSeek/OpenAI，可选，Mock 可离线运行）

## ADDED Requirements

### Requirement: Monorepo 工程骨架

The system SHALL 提供统一 monorepo：Python 后端（FastAPI + Pydantic + SQLAlchemy + SQLite + asyncio）、React 前端（Vite + TS + Tailwind）、共享 packages 目录，并配置 pytest / ruff / mypy / pre-commit 与基础日志、配置管理。

#### Scenario: 骨架就绪
- **WHEN** 开发者克隆仓库并安装依赖
- **THEN** 后端测试与 lint 通过，前端可 `vite dev` 启动空白控制台页面

### Requirement: Agent Runtime 与 Harness

The system SHALL 提供 AgentHarness（prepare/build_context/resolve_tools/check_policy/execute/observe/finalize）与 AgentRuntime 执行循环，围绕统一 AgentState（run_id、agent_id、task、messages、context、tool_results、observations、memory、step、token_usage、cost、status）工作，并支持 max_steps、timeout、retry、cancellation、checkpoint、resume 与失败处理。

#### Scenario: Mock 链路跑通
- **WHEN** 使用 Mock LLM + Mock Tool 提交一个任务
- **THEN** Runtime 执行循环完成并返回最终结果，关键动作产生 Event，状态与 checkpoint 可查询

#### Scenario: 失败重试
- **WHEN** 某工具首次调用失败
- **THEN** Runtime 记录 FAILED observation、更新 context 并重试，第二次成功时 Trace 中可见 Attempt1 FAILED / Attempt2 SUCCESS

#### Scenario: 预算停止
- **WHEN** Agent 执行步数超过 max_steps
- **THEN** Runtime 以 BUDGET_EXCEEDED 终止运行，Trace 记录失败原因

### Requirement: Context Engine

The system SHALL 按 Pipeline（Collect→Rank→Compress→Budget→Assemble）组装上下文，来源含 System Prompt / Task / Conversation / Memory / Tool Schema / Tool Result / Policy / Agent Metadata，并支持 token 预算分配与超限压缩（摘要化、保留关键事实）。

#### Scenario: 上下文超限压缩
- **WHEN** 组装的上下文超过配置的 token 预算
- **THEN** 引擎压缩历史与 observation 并保留关键事实，最终 context 不超过预算

### Requirement: LLM Provider 抽象与 LLMFactory

The system SHALL 定义统一 `LLMProvider.chat(messages, tools=None, model=None)` 接口，并通过 **LLMFactory** 按配置创建 DeepSeek、OpenAI、OpenAI-compatible 或 Mock provider 实例；默认 provider 由环境变量/配置文件决定，Mock provider 必须支持离线完整 Demo。

#### Scenario: 工厂切换 provider
- **WHEN** 配置 `LLM_PROVIDER=deepseek` 或 `mock`
- **THEN** LLMFactory 返回对应 provider，Runtime 无需改动即可运行

### Requirement: Tool Registry 与 Tool Gateway

The system SHALL 要求所有工具经 Tool Gateway 调用，Gateway 依据注册元数据（name/description/schema/risk_level/timeout/cost/permission）执行 Policy 检查后分发到本地工具或 MCP 工具；MCP Client/Server 作为集成协议提供 search/filesystem/database/calculator 示例 Server。

#### Scenario: Gateway 拦截
- **WHEN** Agent 请求调用任一工具
- **THEN** 请求必经 Tool Gateway → Policy 检查 → 实际工具执行，全程产生 tool.request / policy.checked / tool.started / tool.completed 事件

### Requirement: Docker Sandbox

The system SHALL 在 Docker 容器中执行 `python.execute`，默认限制 network disabled、timeout 30s、内存 512MB、CPU 1、临时文件系统，预装 pandas/numpy/matplotlib，并收集 artifacts（如 distribution.png）返回结构化结果。

#### Scenario: 沙箱执行与限制
- **WHEN** Agent 调用 python.execute 运行分析代码
- **THEN** 代码在受限容器内执行并返回 stdout/artifacts；网络访问、超时、内存超限、非法代码均被正确拦截并记录

### Requirement: Policy Engine 与人工审批

The system SHALL 提供 Policy Engine 支持 ALLOW / DENY / REQUIRE_APPROVAL 三级动作与风险等级（LOW/MEDIUM/HIGH/CRITICAL）；REQUIRE_APPROVAL 的工具调用必须暂停运行并在 UI 弹出审批，Approve 后继续执行，Reject 后终止该调用并记录审计事件。

#### Scenario: 高风险工具审批
- **WHEN** Agent 请求调用 database.write（HIGH, require_approval）
- **THEN** UI 展示审批卡片（Tool/Risk/Reason + Approve/Reject），用户选择后运行继续或终止，approval 全程留痕

### Requirement: Event / Trace / Cost / Audit

The system SHALL 以统一 Event 模型（id/run_id/type/timestamp/sequence/payload）记录运行全程，构建 Trace Tree（Run→Context→LLM→Tool→Sandbox→Final）并统计 token 用量、成本、延迟、步数、工具调用数；Cost Tracker 按模型价格汇总 Run 级成本。

#### Scenario: Trace 可视化
- **WHEN** 一次 Run 完成后打开 Trace 页面
- **THEN** 可见时间线（Context Build / LLM Request / Tool / Sandbox / Final）、每个 Span 的 Input/Output/Policy/Sandbox 详情，以及 Tokens/Cost/Latency/Steps/Tool Calls 汇总，数据全部来自真实运行

### Requirement: Evaluation 与 A/B 实验

The system SHALL 提供 Evaluation Runner：Dataset（≥30 cases）→ 指定 Agent 版本运行 → 收集 Trace → Evaluator 打分 → Report；评价维度至少含 Task Success、Tool Selection、Evidence、Policy、Latency、Cost、Steps；支持离线 A/B 实验比较两个 Agent 版本的 Success/Quality/Cost/Latency。

#### Scenario: 版本对比报告
- **WHEN** 对 research-agent v1.0 与 v1.1 在 Research-v1 数据集上运行评估
- **THEN** 报告展示两个版本的 Success%/Cost/Latency 对比表格，数据来自真实运行结果

### Requirement: Web UI（Agent Engineer Console）

The system SHALL 提供控制台 UI：Overview（Runs/Success%/Cost/Latency 指标卡 + Recent Runs）、Agents（详情 + Run/Evaluate/View Trace/Edit）、Runs、Traces（时间线 + Span 详情，最重要页面）、Tools、Sandbox（镜像/网络/资源/artifacts）、Policies（Tool×Risk×Action 表）、Evaluations（版本对比表）、Experiments、Settings；所有指标必须来自真实运行数据。

#### Scenario: 控制台巡检
- **WHEN** 用户打开 http://localhost:3000
- **THEN** 左侧导航完整，Overview 显示真实统计，Trace 页面可逐 Span 展开查看 Input/Output/Policy/Sandbox 信息

### Requirement: Demo Agents

The system SHALL 提供两个 Demo Agent 作为 Runtime 使用者：Research Agent（web.search + document.read + python.execute，产出含证据的对比报告）与 Data Analyst Agent（上传 CSV → 沙箱 Pandas 分析 → 图表 artifact → 结论文本）。

#### Scenario: Research Agent 端到端
- **WHEN** 提交任务"Compare PostgreSQL and MySQL for an AI Agent platform"
- **THEN** Trace 呈现 LLM→Search→Search→Python→LLM→Final 链路，最终报告含 Evidence，UI 展示 Steps/Tokens/Cost/Latency

### Requirement: 一键交付与文档

The system SHALL 提供 `docker compose up` 一键启动完整 Demo、README（Hero 架构图 + 20~40s Demo GIF + Feature cards + 截图 + Quick Start + Architecture + Roadmap）、≥3 张架构图（System / Execution Loop / Governance）与 API 文档；README 中所有指标数字必须来自真实运行。

#### Scenario: 全新环境验收
- **WHEN** 在全新环境 `git clone && docker compose up`
- **THEN** 打开 localhost:3000 可运行 Research Agent 完整链路，最终页面显示 RUN COMPLETED 及真实 Steps/Tool Calls/Tokens/Cost/Latency、Evaluation Success ✓、Policy Violations 0
