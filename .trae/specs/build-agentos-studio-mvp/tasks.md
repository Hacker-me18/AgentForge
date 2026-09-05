# Tasks

按文档 Phase A~J 顺序实施；每阶段完成后运行测试再进入下一阶段。

- [x] Task 1: Phase A — Monorepo 工程骨架
  - [x] 1.1 创建目录结构（apps/api、apps/web、packages/*、agents/、examples/、datasets/、docker/、tests/）与 pyproject.toml
  - [x] 1.2 搭建 FastAPI 后端骨架：配置管理、日志、SQLite + SQLAlchemy 初始化、健康检查接口
  - [x] 1.3 搭建 React + TS + Vite + Tailwind 前端骨架：左侧导航（Overview/Agents/Runs/Traces/Tools/Sandbox/Policies/Evaluations/Experiments/Settings）与空白页面
  - [x] 1.4 配置 pytest / ruff / mypy / pre-commit，建立 Architecture Decision Record（docs/adr/）
  - [x] 1.5 验证：后端 pytest 与 ruff 通过（前端 dev server 验证推迟到 Phase H npm install 后）

- [x] Task 2: Phase B — Agent Runtime 核心
  - [x] 2.1 定义 AgentState（run_id/agent_id/task/messages/context/tool_results/observations/memory/step/token_usage/cost/status）
  - [x] 2.2 实现 AgentHarness 接口（prepare/build_context/resolve_tools/check_policy/execute/observe/finalize）
  - [x] 2.3 实现 AgentRuntime 执行循环：max_steps、timeout、retry、cancellation、failure handling
  - [x] 2.4 实现 Checkpoint 持久化与 resume（SQLite）
  - [x] 2.5 实现 LLMProvider 接口 + LLMFactory（DeepSeek / OpenAI / OpenAI-compatible / Mock，按 LLM_PROVIDER 配置创建）
  - [x] 2.6 验证：Mock LLM + Mock Tool 端到端跑通；失败重试、预算停止（BUDGET_EXCEEDED）测试通过（8 passed）

- [ ] Task 3: Phase C — Tool Registry / Gateway / MCP
  - [ ] 3.1 定义 Tool 接口与 Tool Registry（name/description/schema/risk_level/timeout/cost/permission）
  - [ ] 3.2 实现 Tool Gateway：所有调用经 Gateway 分发
  - [ ] 3.3 实现 MCP Client 与示例 MCP Server（calculator / search / filesystem / database）
  - [ ] 3.4 验证：Gateway 调用本地工具与 MCP 工具均成功，事件完整

- [ ] Task 4: Phase D — Docker Sandbox
  - [ ] 4.1 实现 SandboxRunner + DockerExecutor（python:3.11，预装 pandas/numpy/matplotlib）
  - [ ] 4.2 实现 ResourceLimits（network disabled、timeout 30s、512MB、1 CPU、临时文件系统）与 ArtifactCollector
  - [ ] 4.3 验证：python.execute 成功返回 artifacts；timeout / 内存超限 / 网络禁用 / 非法代码测试通过

- [ ] Task 5: Phase E — Policy Engine 与审批
  - [ ] 5.1 实现 PolicyEngine：Rule / RiskLevel / ALLOW / DENY / REQUIRE_APPROVAL
  - [ ] 5.2 实现 Budget Control（max_steps/max_tokens/max_cost/max_latency，超限 STOP）
  - [ ] 5.3 实现 Approval 模型与 API（审批请求创建、Approve/Reject、审计留痕、运行暂停/恢复）
  - [ ] 5.4 验证：ALLOW/DENY/APPROVAL 三种路径测试通过；database.write 触发审批流

- [ ] Task 6: Phase F — Event / Trace / Cost
  - [ ] 6.1 实现统一 Event 模型（id/run_id/type/timestamp/sequence/payload）与 EventBus / EventStore
  - [ ] 6.2 Runtime 关键动作埋点（run.started、llm.request、tool.request、policy.checked、sandbox.completed、approval.requested、run.completed/failed 等），不侵入业务代码
  - [ ] 6.3 实现 TraceBuilder / Span（Trace Tree）与 CostTracker（按模型价格汇总）
  - [ ] 6.4 验证：一次完整 Run 产生完整 Trace Tree 与 Tokens/Cost/Latency/Steps 汇总

- [ ] Task 7: Phase G — Evaluation 与 A/B
  - [ ] 7.1 实现 Dataset / Case 模型，准备 ≥30 条 Research 评测用例（expected_tools / expected_keywords）
  - [ ] 7.2 实现 Evaluation Runner：运行 → 收集 Trace → Evaluator → Score → Report
  - [ ] 7.3 实现评价维度：Task Success / Tool Selection / Evidence / Policy / Latency / Cost / Steps
  - [ ] 7.4 实现离线 A/B Experiment（Control vs Treatment 版本对比报告）
  - [ ] 7.5 验证：评估可独立运行并输出真实对比报告

- [ ] Task 8: Phase H — Web UI
  - [ ] 8.1 Overview：指标卡（Runs/Success%/Cost/Latency）+ Recent Runs，数据来自真实 API
  - [ ] 8.2 Agents 页面：Agent 详情（Model/Prompt/Tools/Policy/Sandbox）+ Run/Evaluate/View Trace/Edit
  - [ ] 8.3 Traces 页面（最高优先级）：时间线 + Span 详情（Input/Output/Policy/Sandbox）+ Tokens/Cost/Latency/Steps 汇总
  - [ ] 8.4 Runs / Tools / Sandbox / Policies / Evaluations / Experiments 页面
  - [ ] 8.5 Approval 弹窗 UI（Tool/Risk/Reason + Approve/Reject）
  - [ ] 8.6 验证：全页面可用，指标与后端真实数据一致

- [ ] Task 9: Phase I — Demo Agents
  - [ ] 9.1 Research Agent：web.search + document.read + python.execute，产出含证据的对比报告
  - [ ] 9.2 Data Analyst Agent：CSV 上传 → 沙箱 Pandas 分析 → 图表 artifact → 结论
  - [ ] 9.3 预置 Agent/Prompt/Policy 种子数据（research-agent v1.0/v1.1、prompt v1~v3、示例 policy 表）
  - [ ] 9.4 验证：两个 Demo 端到端跑通，Trace 符合预期链路

- [ ] Task 10: Phase J — 交付打磨
  - [ ] 10.1 docker-compose.yml 一键启动（api + web + 沙箱依赖）
  - [ ] 10.2 README：Hero 架构图、Demo GIF（20~40s）、Feature cards、截图、Quick Start、Architecture、Roadmap
  - [ ] 10.3 ≥3 张架构图（System Architecture / Agent Execution Loop / Governance）
  - [ ] 10.4 用真实运行数据替换 README 与 UI 中所有示例数字
  - [ ] 10.5 全新环境验收：git clone → docker compose up → localhost:3000 跑通 Research Agent 完整链路

# Task Dependencies

- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 3]
- [Task 5] depends on [Task 3]
- [Task 6] depends on [Task 2]（可与 Task 3~5 并行开发，集成在其后）
- [Task 7] depends on [Task 6]
- [Task 8] depends on [Task 5, Task 6]（UI 依赖 Policy 审批 API 与 Trace API）
- [Task 9] depends on [Task 4, Task 8]
- [Task 10] depends on [Task 7, Task 9]
