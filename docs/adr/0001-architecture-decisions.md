# ADR 0001: 架构基线决策

日期：2026-09-05
状态：Accepted

## 决策

1. **Monorepo 布局**：`apps/api`（FastAPI 后端）、`apps/web`（React+TS+Vite+Tailwind 前端）、`packages/*`（平台能力包）、`agents/*`（Demo 业务 Agent）。业务 Agent 只是 Runtime 的使用者。
2. **SQLite 优先**：MVP 阶段存储（Registry、Checkpoint、Event、Memory）全部使用 SQLite（aiosqlite），不引入 PostgreSQL/Redis/Kafka 等重型基础设施。
3. **LLM Provider Adapter + LLMFactory**：统一 `LLMProvider.chat(messages, tools, model)` 接口；LLMFactory 按 `AGENTOS_LLM_PROVIDER` 配置创建 deepseek / openai / openai_compatible / mock 实例；mock provider 保证离线 Demo 可跑通。
4. **Tool Gateway 必经**：Agent 不得直接调用工具；所有调用经 Tool Gateway → Policy 检查 → 执行，统一产生事件。MCP 是工具集成协议，不强制所有工具 MCP 化。
5. **Sandbox 默认禁网**：`python.execute` 在 Docker 中运行，network disabled、timeout 30s、内存 512MB、CPU 1、临时文件系统。
6. **Event 驱动可观测**：Runtime 关键动作产生统一 Event（run.started / llm.request / tool.request / policy.checked / ... ），Trace / Cost / Audit 均由 Event 派生，不侵入业务代码。
7. **Control Plane / Data Plane 分离**：Registry / Policy / Evaluation / Experiment 为控制面；Runtime / LLM / Tool / Sandbox / Memory 为数据面。
8. **高风险工具人工审批**：Policy 动作含 ALLOW / DENY / REQUIRE_APPROVAL；审批通过 UI 完成，全程审计留痕。
