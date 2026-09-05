# AgentOS Studio
## 企业级 Agent Runtime & Evaluation Platform
### GitHub Showcase / Demo Project 设计施工方案

> 面向 GitHub 展示的独立 Agent Infrastructure 作品。
> 不绑定德福科技、不绑定制造业、不伪装成某公司的真实项目。
>
> 核心目标：做一个“看起来像真实 Agent Infrastructure 产品、能够完整 Demo、架构有深度、代码可快速 Vibe Coding、截图和文档专业”的开源作品。
>
> 推荐名称：**AgentOS Studio**
>
> 副标题：**An Open Agent Runtime, Harness & Evaluation Platform**
>
> 一句话：**Build, run, trace, evaluate and govern reliable AI agents.**

---

# 1. 项目定位

不再做普通的 RAG Agent、Coding Agent、Research Agent 或客服 Agent，而是做一个横向的 **Agent Infrastructure / AgentOps 平台**。

核心能力：

```text
BUILD
RUN
OBSERVE
EVALUATE
GOVERN
```

也就是：

```text
Agent 定义
  ↓
Harness / Runtime
  ↓
Context / Memory / Tools / MCP / Sandbox
  ↓
Policy / Budget / Approval
  ↓
Event / Trace / Cost / Audit
  ↓
Evaluation / A-B Experiment
```

核心价值：

> 让 Agent 从“能调用 LLM”变成“可运行、可观察、可评估、可治理”。

---

# 2. 产品故事

普通 Agent：

```text
User → Prompt → LLM → Tool → Answer
```

AgentOS Studio：

```text
User Task
   ↓
Agent
   ↓
Harness
   ↓
Context
   ↓
LLM
   ↓
Tool Gateway
   ↓
Policy
   ↓
MCP / Tool
   ↓
Sandbox
   ↓
Observation
   ↓
Context Update
   ↓
Next Step
   ↓
Final
   ↓
Trace / Cost / Audit
   ↓
Evaluation / A-B
```

项目真正展示的是 **Agent 的运行基础设施**，而不是某一个业务 Agent。

---

# 3. Demo 场景

平台本身不绑定业务，但需要 Demo Agent。

## Demo 1：Research Agent

用户：

> Compare PostgreSQL and MySQL for an AI Agent platform. Collect evidence, analyze trade-offs, and produce a recommendation.

流程：

```text
Task
 ↓
Research Plan
 ↓
Search Tool
 ↓
Document Tool
 ↓
Python Analysis
 ↓
Context Update
 ↓
Final Report
```

优势：

- 不绑定企业；
- 易理解；
- 能展示 Tool Calling；
- 能展示 Context；
- 能展示 Sandbox；
- 能展示多步骤 Agent；
- 容易展示 Trace 和 Evaluation。

## Demo 2：Data Analyst Agent

上传 CSV：

```text
sales.csv
```

任务：

> Analyze this CSV and explain the main anomalies.

流程：

```text
Upload
 ↓
Agent
 ↓
Python Tool
 ↓
Docker Sandbox
 ↓
Pandas / NumPy
 ↓
Statistical Analysis
 ↓
Chart / Artifact
 ↓
Final Explanation
```

## Demo 3：Governance

创建高风险 Tool：

```text
database.write
```

Agent 请求调用：

```text
Tool Request
 ↓
Policy Engine
 ↓
REQUIRE_APPROVAL
 ↓
Human
 ├── Approve
 └── Reject
```

---

# 4. 总体架构

```text
                          ┌───────────────┐
                          │   Web UI      │
                          │ Agent Studio  │
                          └───────┬───────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │ API Gateway   │
                          └───────┬───────┘
                                  │
                                  ▼
                    ┌────────────────────────┐
                    │     Control Plane      │
                    │                        │
                    │ Agent Registry         │
                    │ Prompt Registry        │
                    │ Tool Registry           │
                    │ Policy                 │
                    │ Evaluation              │
                    │ Experiments             │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │      Agent Runtime      │
                    │                        │
                    │ Harness                │
                    │ Execution Loop         │
                    │ Context Engine         │
                    │ Memory                 │
                    │ Checkpoint             │
                    └───────────┬────────────┘
                                │
                ┌───────────────┼────────────────┐
                ▼               ▼                ▼
             LLM Router      Tool Gateway     Sandbox
                │               │                │
                ▼               ▼                ▼
          DeepSeek/OpenAI      MCP           Docker
                               Tools          Python
                │
                └────────────────┬──────────────┘
                                 ▼
                       ┌──────────────────┐
                       │ Event / Trace    │
                       │ Cost / Audit     │
                       └────────┬─────────┘
                                ▼
                       ┌──────────────────┐
                       │ Evaluation       │
                       │ Dataset / A-B    │
                       └──────────────────┘
```

---

# 5. Control Plane / Data Plane

这是项目建议重点体现的架构思想。

## Control Plane

```text
Agent Registry
Prompt Version
Tool Registry
Policy
Evaluation
Experiment
```

## Data Plane

```text
Agent Runtime
LLM
Tool
MCP
Sandbox
Memory
Execution
```

关系：

```text
Control Plane
     │
     │ configuration
     ▼
Data Plane
     │
     │ execution
     ▼
Event / Trace
```

这样项目更像一个真正的平台，而不是 LangGraph Wrapper。

---

# 6. Agent Registry

Agent 定义示例：

```yaml
name: research-agent
version: 1.2.0

model:
  provider: deepseek
  name: deepseek-chat

prompt:
  version: v3

tools:
  - web.search
  - document.read
  - python.execute

policy:
  max_steps: 15
  max_cost: 0.5

sandbox:
  enabled: true
```

支持：

```text
Create
Version
Publish
Rollback
Archive
```

---

# 7. Prompt Registry

Prompt 不直接写死在代码里：

```text
Prompt
 ↓
Version
 ↓
Evaluation
 ↓
Publish
```

例如：

```text
research-agent

v1
v2
v3
```

可查看：

```text
Prompt Diff
Evaluation Score
Latency
Cost
```

---

# 8. Agent Harness

Harness 是核心模块之一。

职责：

```text
Task
Context
Prompt
Tools
Memory
Policy
Runtime
```

推荐接口：

```python
class AgentHarness:
    async def prepare(self, task): ...
    async def build_context(self, state): ...
    async def resolve_tools(self, state): ...
    async def check_policy(self, action): ...
    async def execute(self, action): ...
    async def observe(self, result): ...
    async def finalize(self, state): ...
```

Harness 不负责具体业务逻辑。

---

# 9. Agent Runtime

Runtime 负责执行循环：

```text
while not finished:

    context = harness.build_context()

    response = llm.generate(context)

    if response.tool_call:

        policy.check()

        result = tool.execute()

        context.update(result)

        checkpoint.save()

    else:

        return response
```

必须支持：

- max_steps
- timeout
- retry
- cancellation
- checkpoint
- resume
- failure handling

---

# 10. Runtime State

统一 Agent State：

```python
AgentState(
    run_id,
    agent_id,
    task,
    messages,
    context,
    tool_results,
    observations,
    memory,
    step,
    token_usage,
    cost,
    status
)
```

LLM、Tool、Sandbox、Trace、Evaluation 全部围绕 State 工作。

---

# 11. Context Engine

Context 来源：

```text
System Prompt
+
User Task
+
Conversation
+
Memory
+
Tool Schema
+
Tool Result
+
Policy
+
Agent Metadata
```

Pipeline：

```text
Collect
 ↓
Rank
 ↓
Compress
 ↓
Budget
 ↓
Assemble
```

Context Budget 示例：

```text
Total Context: 16K

System:      1K
Task:        1K
History:     4K
Tools:       3K
Memory:      2K
Observation: 5K
```

超限：

```text
Context
 ↓
Token Estimate
 ↓
Compression
 ↓
Summary
 ↓
Keep Critical Facts
```

---

# 12. Tool Gateway

Agent 不直接调用 Tool：

```text
Agent
 ↓
Tool Gateway
 ↓
Policy
 ↓
Tool
```

Tool metadata：

```text
name
description
schema
risk_level
timeout
cost
permission
```

例如：

```yaml
name: python.execute
risk_level: medium
timeout: 30
network: false
```

---

# 13. MCP

MCP 用于展示现代 Agent Tool Integration。

```text
Agent
 ↓
Tool Gateway
 ↓
MCP Client
 ↓
MCP Server
 ↓
External Tool
```

Demo MCP Server：

```text
search
filesystem
database
calculator
```

关键架构思想：

> MCP 是 Tool Integration Protocol；Tool Gateway 是平台治理入口。

不要为了“使用 MCP”而强行让所有工具都 MCP 化。

---

# 14. Sandbox

Sandbox 是 GitHub Demo 的视觉亮点。

```text
Agent
 ↓
python.execute
 ↓
Policy
 ↓
Docker Sandbox
 ↓
Python
 ↓
Result
```

建议限制：

```text
network = disabled
timeout = 30s
memory = 512MB
cpu = 1
ephemeral filesystem
```

支持：

```text
pandas
numpy
matplotlib
```

返回：

```json
{
  "status": "success",
  "artifacts": ["distribution.png"],
  "summary": "..."
}
```

---

# 15. Policy Engine

Policy：

```text
ALLOW
DENY
REQUIRE_APPROVAL
```

示例：

```yaml
tools:
  web.search:
    action: allow

  document.read:
    action: allow

  python.execute:
    action: allow

  database.read:
    action: allow

  database.write:
    action: require_approval

  shell.execute:
    action: deny
```

---

# 16. Budget Control

Agent 运行预算：

```text
max_steps
max_tokens
max_cost
max_latency
```

例如：

```yaml
max_steps: 15
max_tokens: 20000
max_cost: 0.50
timeout: 120
```

超限：

```text
Budget Exceeded
 ↓
STOP
```

---

# 17. Human-in-the-loop

高风险 Tool：

```text
Agent
 ↓
Tool Request
 ↓
Policy
 ↓
Approval Required
 ↓
UI
```

UI：

```text
┌──────────────────────────────┐
│ Approval Required            │
│                              │
│ Tool: database.write         │
│ Risk: HIGH                   │
│ Reason: Update records       │
│                              │
│ [ Reject ]    [ Approve ]    │
└──────────────────────────────┘
```

---

# 18. Event Architecture

所有运行过程产生 Event：

```text
run.started
context.created
llm.request
llm.response
tool.request
policy.checked
tool.started
tool.completed
sandbox.started
sandbox.completed
checkpoint.created
approval.requested
run.completed
run.failed
```

统一模型：

```python
Event(
    id,
    run_id,
    type,
    timestamp,
    sequence,
    payload
)
```

---

# 19. Tracing

Trace Tree：

```text
Run
│
├── Context
│
├── LLM
│   ├── Request
│   └── Response
│
├── Tool
│   ├── Search
│   └── Document
│
├── Sandbox
│   └── Python
│
├── LLM
│
└── Final
```

UI 展示：

```text
Latency
Tokens
Cost
Tool
Input
Output
Status
```

---

# 20. Cost Tracking

每次 LLM：

```text
input_tokens
output_tokens
model
price
cost
```

Run 汇总：

```text
Total Tokens
Total Cost
LLM Calls
Tool Calls
Sandbox Time
```

Dashboard：

```text
Daily Runs
Success Rate
Token Usage
Estimated Cost
Average Latency
```

---

# 21. Evaluation

不要只评价最终文本。

至少评价：

```text
Task Success
Tool Selection
Evidence
Policy
Latency
Cost
Steps
```

Dataset：

```json
{
  "id": "case-001",
  "task": "Compare PostgreSQL and MySQL...",
  "expected_tools": [
    "web.search",
    "python.execute"
  ],
  "expected_keywords": [
    "PostgreSQL",
    "MySQL"
  ]
}
```

---

# 22. Evaluation Runner

```text
Dataset
 ↓
Agent Version
 ↓
Run
 ↓
Collect Trace
 ↓
Evaluator
 ↓
Score
 ↓
Report
```

示例：

```text
Agent v1.0
Success: 72%
Cost: $0.21
Latency: 8.2s

Agent v1.1
Success: 86%
Cost: $0.19
Latency: 7.5s
```

> 数字仅为 UI 示例，项目完成后必须使用真实运行结果。

---

# 23. A/B Testing

实验：

```text
Experiment #001

Control:
research-agent v1.0

Treatment:
research-agent v1.1
```

比较：

```text
Success
Quality
Cost
Latency
```

MVP 不需要大规模在线流量系统，使用离线 Evaluation + 模拟流量即可。

---

# 24. Memory

MVP 保持简单：

```text
Short-term Memory
Long-term Memory
```

Short-term：

```text
Conversation
Agent State
Tool Results
```

Long-term：

```text
User Preferences
Previous Findings
Important Facts
```

存储：

```text
SQLite
```

未来再接：

```text
PostgreSQL
Redis
Vector DB
```

---

# 25. Agent Framework Adapter

不要把 AgentOS 绑定死在一个框架上：

```text
AgentOS Runtime
      │
      ├── Native Agent
      ├── LangGraph Adapter
      └── Future Framework
```

核心思想：

> LangGraph 是可插拔执行框架，而不是 AgentOS 本身。

---

# 26. LLM Provider Adapter

统一：

```text
LLMProvider
```

支持：

```text
DeepSeek
OpenAI
Local / OpenAI-compatible
```

接口：

```python
class LLMProvider:
    async def chat(messages, tools=None, model=None):
        ...
```

---

# 27. 推荐技术栈

## Backend

```text
Python
FastAPI
Pydantic
SQLAlchemy
SQLite
asyncio
```

## Agent

```text
LangGraph
Custom Runtime
Tool Calling
MCP
```

## Sandbox

```text
Docker
```

## Frontend

```text
React
TypeScript
Vite
TailwindCSS
```

## Observability

```text
OpenTelemetry-compatible event model
```

MVP 可先使用自建 Event/Trace。

## Evaluation

```text
Custom Evaluation Runner
Ragas Adapter（可选）
```

---

# 28. MVP 不建议引入

不要为了“看起来高级”堆：

```text
Kubernetes
Kafka
Redis Cluster
PostgreSQL Cluster
Firecracker
MicroVM
Service Mesh
Ray
复杂微服务
复杂消息队列
```

价值来自：

> **完整 Agent Infrastructure 闭环，而不是基础设施数量。**

---

# 29. 推荐项目目录

```text
agentos-studio/

├── apps/
│   ├── api/
│   └── web/
│
├── packages/
│   ├── runtime/
│   │   ├── harness/
│   │   ├── execution/
│   │   ├── state/
│   │   ├── checkpoint/
│   │   └── lifecycle/
│   │
│   ├── context/
│   ├── memory/
│   ├── tools/
│   │   ├── gateway/
│   │   ├── registry/
│   │   └── mcp/
│   │
│   ├── sandbox/
│   ├── policy/
│   ├── tracing/
│   ├── evaluation/
│   ├── llm/
│   └── adapters/
│
├── agents/
│   ├── research/
│   └── data_analyst/
│
├── examples/
├── datasets/
├── docker/
├── docs/
├── screenshots/
├── tests/
├── docker-compose.yml
├── pyproject.toml
├── README.md
└── LICENSE
```

---

# 30. UI 产品结构

不要做传统后台管理系统。

定位：

> **AI Developer / Agent Engineer Console**

左侧：

```text
AgentOS

Overview
Agents
Runs
Traces
Tools
Sandbox
Evaluations
Experiments
Policies
Settings
```

---

# 31. Overview 页面

```text
┌─────────────────────────────────────────────────┐
│ AgentOS Studio                                  │
│ Agent Runtime & Evaluation Platform             │
├────────────┬────────────┬────────────┬──────────┤
│ 1,248 Runs │ 87.4%      │ $12.42     │ 4.8s     │
│            │ Success    │ Cost       │ Latency  │
└────────────┴────────────┴────────────┴──────────┘

Recent Runs

Research Agent
██████████████████████
Completed · 8.2s · $0.04

Data Analyst
████████████████
Completed · 12.1s · $0.08
```

数字最终必须替换为真实 Demo 数据。

---

# 32. Agent 页面

```text
Research Agent

Status: Published
Version: v1.2

Model
DeepSeek

Prompt
v3

Tools
3

Policy
Standard

Sandbox
Enabled
```

按钮：

```text
Run
Evaluate
View Trace
Edit
```

---

# 33. Trace 页面

这是整个项目最重要的截图。

```text
Research Agent
Run #7F82

Task
└── Compare PostgreSQL and MySQL...

Timeline

00:00 Context Build
00:01 LLM Request
00:02 Tool: web.search
00:04 Tool: document.read
00:05 Sandbox: python.execute
00:07 Context Update
00:08 LLM Request
00:09 Final Answer

──────────────────────────

Tokens      4,218
Cost        $0.041
Latency     9.2s
Steps       7
Tool Calls  3
```

---

# 34. Trace Detail

点击 Span：

```text
Tool: python.execute

Input
------------------
code:
...

Policy
------------------
ALLOW

Sandbox
------------------
Docker
Network: Disabled
Timeout: 30s

Output
------------------
...
```

这是 GitHub README 最值得展示的页面之一。

---

# 35. Evaluation 页面

```text
Evaluation

Dataset
Research-v1

┌──────────────┬────────┬────────┬────────┐
│ Agent        │ Success│ Cost   │ Latency│
├──────────────┼────────┼────────┼────────┤
│ v1.0         │ 72%    │ $0.21  │ 8.2s   │
│ v1.1         │ 86%    │ $0.19  │ 7.5s   │
└──────────────┴────────┴────────┴────────┘
```

---

# 36. Policy 页面

```text
Tool Governance

Tool                  Risk      Action

web.search             LOW       ALLOW
document.read          LOW       ALLOW
python.execute         MEDIUM    ALLOW
database.read          MEDIUM    ALLOW
database.write         HIGH      APPROVAL
shell.execute          CRITICAL  DENY
```

---

# 37. Sandbox 页面

```text
Sandbox Run #92A1

Image
python:3.11

Network
OFF

CPU
1

Memory
512 MB

Timeout
30 sec

Status
SUCCESS

Artifacts
distribution.png
analysis.json
```

---

# 38. GitHub README 第一屏

不要一上来放大量代码。

推荐：

```text
# AgentOS Studio

### Build · Run · Trace · Evaluate · Govern AI Agents

[Demo] [Architecture] [Quick Start] [Documentation]
```

然后放：

1. Hero Architecture 图
2. Demo GIF
3. Feature cards
4. Screenshots
5. Quick Start
6. Architecture
7. Technical Design
8. Roadmap

Feature cards：

```text
Runtime      MCP
Sandbox      Context
Policy       Tracing
Evaluation   A/B
```

---

# 39. Demo GIF

必须制作一个 20~40 秒 GIF：

```text
Create Agent
 ↓
Run Agent
 ↓
Tool Call
 ↓
Sandbox
 ↓
Trace
 ↓
Evaluation
```

GitHub 用户不用看代码就能理解项目。

---

# 40. README 截图顺序

推荐：

1. Agent Runtime Overview
2. Agent Run / Trace
3. Tool + MCP
4. Sandbox
5. Policy / Approval
6. Evaluation
7. A/B Experiment

---

# 41. Architecture 图

至少三张。

## 图 1：System Architecture

```text
Control Plane
+
Runtime
+
Tools
+
Sandbox
+
Observability
```

## 图 2：Agent Execution Loop

```text
Task
 ↓
Context
 ↓
LLM
 ↓
Tool
 ↓
Observation
 ↓
Context
 ↓
LLM
```

## 图 3：Governance

```text
Agent
 ↓
Policy
 ├── Allow
 ├── Deny
 └── Approval
       ↓
    Sandbox
```

---

# 42. Demo 1：Research Agent

输入：

```text
Compare PostgreSQL and MySQL
for an AI Agent platform.
```

Trace 示例：

```text
LLM → Search → Search → Python → LLM → Final
```

最终在 UI 展示：

```text
Evidence
Tool Calls
Steps
Tokens
Cost
Latency
```

---

# 43. Demo 2：Data Analyst

上传：

```text
sales.csv
```

执行：

```text
Agent
 ↓
Python
 ↓
Docker Sandbox
 ↓
Pandas
 ↓
Chart
 ↓
Answer
```

---

# 44. Demo 3：Governance

创建：

```text
database.write
```

Agent：

```text
Call Tool
```

系统：

```text
Policy
 ↓
REQUIRE_APPROVAL
```

用户：

```text
Approve
```

然后：

```text
Tool Execute
 ↓
Trace
 ↓
Audit
```

---

# 45. Demo 4：Failure Recovery

让 Tool 第一次失败：

```text
Tool Error
```

Runtime：

```text
Retry
 ↓
Observation
 ↓
Context Update
 ↓
Second Attempt
 ↓
Success
```

Trace：

```text
Attempt 1
FAILED

Attempt 2
SUCCESS
```

这个 Demo 很适合体现 Runtime 的价值。

---

# 46. Demo 5：Budget Stop

设置：

```text
max_steps = 5
```

Agent 超过：

```text
Step 6
```

Runtime：

```text
BUDGET_EXCEEDED
```

停止。

Trace：

```text
Run Failed
Reason:
Step budget exceeded
```

---

# 47. MVP 开发顺序

不要让 Claude Code / Codex 一次性生成整个项目。

按：

```text
Phase A  Architecture
Phase B  Runtime
Phase C  Tools / MCP
Phase D  Sandbox
Phase E  Policy
Phase F  Trace
Phase G  Evaluation
Phase H  UI
Phase I  Demo
Phase J  README / Screenshots
```

每个阶段：

```text
Implement
 ↓
Test
 ↓
Fix
 ↓
Commit
 ↓
Continue
```

---

# 48. Phase A：Skeleton

完成：

```text
monorepo
backend
frontend
packages
database
config
logging
```

建议工程工具：

```text
pytest
ruff
mypy
pre-commit
```

---

# 49. Phase B：Runtime

先实现：

```text
AgentState
AgentHarness
AgentRuntime
ExecutionLoop
Checkpoint
Retry
Timeout
Cancellation
```

首先测试：

```text
Task
 ↓
Mock LLM
 ↓
Mock Tool
 ↓
Final
```

---

# 50. Phase C：Tool / MCP

实现：

```text
Tool Interface
Tool Registry
Tool Gateway
MCP Client
MCP Server
```

先做：

```text
calculator
search
document
```

---

# 51. Phase D：Sandbox

实现：

```text
SandboxRunner
DockerExecutor
ResourceLimits
ArtifactCollector
```

测试：

```text
python.execute
```

必须测试：

```text
timeout
memory
network disabled
invalid code
```

---

# 52. Phase E：Policy

实现：

```text
PolicyEngine
Rule
RiskLevel
Approval
Budget
```

测试：

```text
ALLOW
DENY
APPROVAL
```

---

# 53. Phase F：Trace

实现：

```text
EventBus
EventStore
TraceBuilder
Span
CostTracker
```

原则：

```text
Runtime
 ↓
Event
 ↓
Trace / Cost / Audit
```

Trace 不应侵入业务 Agent 逻辑。

---

# 54. Phase G：Evaluation

实现：

```text
Dataset
Case
Runner
Evaluator
Metrics
Report
```

先准备：

```text
30 cases
```

不需要大数据集。

---

# 55. Phase H：UI

页面：

```text
Dashboard
Agents
Runs
Trace
Tools
Sandbox
Policies
Evaluation
Experiments
```

优先级：

```text
Trace
 >
Dashboard
 >
Evaluation
 >
Policy
```

---

# 56. Phase I：Demo Agent

先做：

```text
Research Agent
```

然后：

```text
Data Analyst Agent
```

业务 Agent 只是 Runtime 的使用者。

---

# 57. Phase J：GitHub Polish

最终：

```text
README
Architecture
Quick Start
Demo GIF
Screenshots
API docs
Examples
Tests
Docker Compose
```

发布：

```text
v0.1.0
```

---

# 58. Definition of Done

MVP 至少实现：

- [ ] Agent Registry
- [ ] Prompt Version
- [ ] Agent Harness
- [ ] Agent Runtime
- [ ] Context Engine
- [ ] Tool Registry
- [ ] Tool Gateway
- [ ] MCP
- [ ] Docker Sandbox
- [ ] Policy Engine
- [ ] Human Approval
- [ ] Session
- [ ] Event
- [ ] Trace
- [ ] Cost
- [ ] Checkpoint
- [ ] Retry
- [ ] Evaluation
- [ ] A/B Experiment
- [ ] Research Agent
- [ ] Data Analyst Agent
- [ ] Web UI
- [ ] Docker Compose
- [ ] README
- [ ] Architecture Diagram
- [ ] Demo GIF
- [ ] Screenshots

---

# 59. 项目核心技术关系

这是整个项目最重要的一张逻辑图：

```text
                    Agent
                      │
                      ▼
                  Harness
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       Context       Tools      Policy
          │           │           │
          │           ▼           │
          │          MCP          │
          │           │           │
          │           ▼           │
          │        Sandbox        │
          │           │           │
          └───────────┼───────────┘
                      ▼
                    Runtime
                      │
                      ▼
                   Events
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
        Trace        Cost       Audit
                      │
                      ▼
                  Evaluation
                      │
                      ▼
                    A/B
```

---

# 60. 与普通 Agent 项目的区别

普通项目：

```text
User
 ↓
LangGraph
 ↓
LLM
 ↓
Tool
 ↓
Answer
```

AgentOS：

```text
Agent
 ↓
Harness
 ↓
Runtime
 ├── Context
 ├── Memory
 ├── Tool
 ├── MCP
 ├── Sandbox
 ├── Policy
 ├── Budget
 ├── Checkpoint
 └── Retry
       ↓
     Events
       ↓
Trace / Audit / Cost
       ↓
Evaluation
       ↓
A/B
```

---

# 61. Roadmap

README Roadmap：

```text
v0.1
Local Agent Runtime

v0.2
MCP Ecosystem

v0.3
Evaluation & Experiments

v0.4
Multi-Agent Runtime

v0.5
Distributed Execution

v0.6
PostgreSQL / Redis

v0.7
Kubernetes Runtime

v1.0
Production-grade Agent Platform
```

未来可选：

```text
Multi-Agent
A2A
Distributed Runtime
OpenTelemetry
Remote Sandbox
Agent Marketplace
Prompt Optimization
Online Evaluation
LLM Router
Model Fallback
Semantic Cache
```

---

# 62. 最终 GitHub 展示目标

用户打开仓库后，30 秒内理解：

```text
这是什么？
 ↓
Agent Runtime Platform

能干什么？
 ↓
Build / Run / Trace / Evaluate / Govern

有什么技术？
 ↓
Harness
Runtime
MCP
Sandbox
Context
Policy
Tracing
Evaluation

能跑吗？
 ↓
Docker Compose

效果如何？
 ↓
Demo GIF + Screenshots

怎么设计的？
 ↓
Architecture
```

---

# 63. 最终项目一句话

> **AgentOS Studio is an open-source Agent Infrastructure platform that provides a unified runtime, harness, context management, tool/MCP integration, sandbox execution, governance, tracing, evaluation and experimentation layer for reliable AI agents.**

中文：

> **AgentOS Studio 是一个面向 AI Agent 的开源基础设施平台，通过统一 Harness / Runtime / Context / Tool / MCP / Sandbox / Policy / Tracing / Evaluation 能力，让 Agent 从“能调用模型”进一步走向“可运行、可观察、可评估、可治理”。**

---

# 64. 给 Claude Code / Codex 的总施工原则

1. 先读本 Spec，不得直接开始大量编码。
2. 先建立 Architecture Decision Record。
3. 先定义 interfaces，再写 implementations。
4. Runtime 与业务 Agent 解耦。
5. 所有 Tool 必须经过 Tool Gateway。
6. 高风险 Tool 必须经过 Policy。
7. Sandbox 默认 network disabled。
8. Runtime 关键动作必须产生 Event。
9. Trace 不应该侵入业务代码。
10. Evaluation 必须能够独立运行。
11. LLM Provider 必须 Adapter 化。
12. Agent Framework 必须 Adapter 化。
13. SQLite 优先，避免过早引入复杂基础设施。
14. 每阶段完成后运行测试。
15. 不为了技术名词增加没有实际价值的组件。
16. README、架构图、Demo、截图与代码同步建设。
17. 所有指标必须来自真实运行结果，不得伪造。
18. 最终提供一键 Docker Compose Demo。

---

# 65. 最终验收场景

从全新的环境：

```bash
git clone ...
docker compose up
```

打开：

```text
http://localhost:3000
```

执行：

```text
Research Agent
 ↓
Run
 ↓
LLM
 ↓
Tool
 ↓
MCP
 ↓
Sandbox
 ↓
Trace
 ↓
Evaluation
```

最终页面出现真实运行结果：

```text
RUN COMPLETED

Steps       N
Tool Calls  N
Tokens      N
Cost        $N
Latency     N sec

Evaluation
Success ✓

Policy Violations
0
```

**只要这条链真正跑通，AgentOS Studio 就已经是一个完整、有展示价值的 GitHub Agent Infrastructure 作品。**
