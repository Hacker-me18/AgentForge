# Checklist

## Phase A 骨架
- [x] monorepo 目录结构与 docs 推荐布局一致（apps/api、apps/web、packages/*、agents/）
- [x] pytest / ruff / mypy / pre-commit 配置并全部通过（pytest 1 passed；ruff clean；mypy 配置就绪）
- [x] ADR 已建立（docs/adr/0001-architecture-decisions.md）
- [ ] 前端 dev server 可启动并展示左侧导航（推迟到 Phase H npm install 后验证）

## Phase B Runtime
- [x] AgentState 字段完整（run_id/agent_id/task/messages/context/tool_results/observations/memory/step/token_usage/cost/status）
- [x] AgentHarness 七个接口方法实现且不含业务逻辑
- [x] 执行循环支持 max_steps / timeout / retry / cancellation / checkpoint / resume / failure handling
- [x] Mock LLM + Mock Tool 端到端测试通过
- [x] 工具首次失败 → 重试成功，observations 可见 FAILED→SUCCESS（Trace 展示在 Phase F 验证）
- [x] 超过 max_steps 时以 BUDGET_EXCEEDED 终止
- [x] LLMFactory 按配置创建 DeepSeek / OpenAI / OpenAI-compatible / Mock provider，切换无需改 Runtime

## Phase C Tool / MCP
- [x] Tool Registry 元数据完整（name/description/schema/risk_level/timeout/cost/permission）
- [x] 所有工具调用必经 Tool Gateway（无绕过路径）
- [x] MCP Client 可调通示例 MCP Server（calculator/search/filesystem/database，stdio JSON-RPC 端到端测试通过）

## Phase D Sandbox
- [x] python.execute 在 Docker 中运行，预装 pandas/numpy/matplotlib（agentos-sandbox:0.1）
- [x] 限制生效：network disabled、timeout 30s、512MB、1 CPU、每轮全新临时目录（bind-mount，tmpfs 无法回收 artifacts）
- [x] timeout / 内存超限 / 网络访问 / 非法代码均被拦截并记录
- [x] artifacts（图片/json）可收集并返回（matplotlib png 测试通过）

## Phase E Policy
- [ ] ALLOW / DENY / REQUIRE_APPROVAL 三种动作测试通过
- [ ] Budget（max_steps/max_tokens/max_cost/max_latency）超限即 STOP
- [ ] database.write 触发审批：UI 卡片 Approve 继续 / Reject 终止，全程审计留痕

## Phase F Trace
- [ ] Event 模型统一（id/run_id/type/timestamp/sequence/payload），覆盖 spec 列出的全部事件类型
- [ ] Trace Tree（Run→Context→LLM→Tool→Sandbox→Final）正确构建
- [ ] Trace 不侵入业务 Agent 逻辑
- [ ] CostTracker 按模型价格汇总 Run 级 Tokens/Cost/Latency/Steps/Tool Calls

## Phase G Evaluation
- [ ] Dataset ≥30 cases，含 expected_tools / expected_keywords
- [ ] Evaluation Runner 可独立运行
- [ ] 评价维度覆盖 Task Success / Tool Selection / Evidence / Policy / Latency / Cost / Steps
- [ ] A/B 实验输出两个版本的真实 Success/Cost/Latency 对比

## Phase H UI
- [ ] 左侧导航含 Overview/Agents/Runs/Traces/Tools/Sandbox/Policies/Evaluations/Experiments/Settings
- [ ] Trace 页面：时间线 + 可展开 Span 详情（Input/Output/Policy/Sandbox）
- [ ] Policies 页面展示 Tool×Risk×Action 表（web.search LOW ALLOW … shell.execute CRITICAL DENY）
- [ ] Approval 弹窗含 Tool/Risk/Reason + Approve/Reject
- [ ] 所有页面指标来自真实运行数据，无硬编码假数据

## Phase I Demo
- [ ] Research Agent 端到端：LLM→Search→Search→Python→LLM→Final，报告含 Evidence
- [ ] Data Analyst Agent：CSV 上传 → 沙箱分析 → 图表 artifact → 结论
- [ ] 种子数据就绪（Agent 版本、Prompt v1~v3、Policy 表）

## Phase J 交付
- [ ] `docker compose up` 一键启动全部服务
- [ ] README 含 Hero 架构图、20~40s Demo GIF、Feature cards、截图、Quick Start、Architecture、Roadmap
- [ ] ≥3 张架构图（System / Execution Loop / Governance）
- [ ] README 与 UI 中所有数字来自真实运行结果
- [ ] 全新环境验收链跑通：clone → compose up → localhost:3000 → Research Agent → RUN COMPLETED（真实 Steps/Tokens/Cost/Latency、Evaluation Success ✓、Policy Violations 0）
