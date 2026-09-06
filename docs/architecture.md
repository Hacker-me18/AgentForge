# AgentOS Studio — Architecture

AgentOS Studio is a **layered, provider-agnostic agent runtime and evaluation
platform**. Each capability lives in its own `packages/*` module and is composed
at runtime by the FastAPI service and by the offline evaluation runner — the
*exact same* components run a live Studio run, a seeded demo run, and an
offline evaluation case. Nothing is mocked at the orchestration layer.

```mermaid
flowchart LR
    subgraph UI["Studio Web (React 18 · Tailwind)"]
        DASH["Overview · Agents · Runs · Traces"]
        EXPL["Tools · Sandbox · Policies"]
        EVAL["Evaluations · Experiments · Settings"]
    end

    subgraph API["Studio API (FastAPI · aiosqlite · no ORM)"]
        REST["REST routers"]
        SVC["RunService"]
    end

    subgraph CORE["Agent runtime"]
        H["AgentHarness"]
        R["AgentRuntime"]
        CTX["ContextEngine"]
        CK["Checkpoint"]
        BUD["Budget"]
    end

    subgraph TOOLS["Tool layer"]
        REG["ToolRegistry"]
        GW["ToolGateway (envelope)"]
        BUILTIN["builtin tools"]
        MCPC["MCP client"]
        SBOX["Docker sandbox"]
    end

    subgraph POL["Governance"]
        PE["PolicyEngine"]
        AP["ApprovalManager"]
        AS["ApprovalStore"]
    end

    subgraph TRC["Observability"]
        BUS["EventBus"]
        ESTORE["EventStore (SQLite)"]
        TB["TraceBuilder"]
    end

    LLM["LLM providers<br/>mock · deepseek · openai"]

    UI -->|fetch /api| API
    API --> SVC --> H
    H --> CTX
    H --> REG --> GW
    GW --> BUILTIN
    GW --> MCPC
    GW --> SBOX
    R --> CK
    R --> BUD
    H -->|tool call| PE
    PE -->|require_approval| AP --> AS
    H -->|events| BUS --> ESTORE --> TB
    R -->|status| API
    API -->|runs table| DASH
    API -->|trace| TRC
    H -->|chat| LLM
```

## 1. Run lifecycle

Every run — seeded, manual, or evaluated — follows the same loop inside
`AgentRuntime`:

```mermaid
sequenceDiagram
    participant U as UI / runner
    participant RS as RunService
    participant RT as AgentRuntime
    participant LLM as LLM
    participant GW as ToolGateway
    participant PE as PolicyEngine
    participant CK as Checkpoint

    U->>RS: start(task, agent_id)
    RS->>RT: run(state)
    loop while tool calls remain and budget/time allow
        RT->>LLM: chat(context, tools)
        alt returns text (no tool calls)
            LLM-->>RT: finish_reason=stop
            RT->>RT: final_answer = content
        else returns tool call(s)
            LLM-->>RT: finish_reason=tool_calls
            loop for each tool call
                RT->>PE: check(tool)
                alt allow
                    PE-->>RT: allow
                    RT->>GW: execute(tool, args)
                    GW-->>RT: {status, output, duration_ms}
                else require_approval
                    PE-->>RT: require_approval
                    RT->>RT: status = waiting_approval
                    RT-->>U: approval requested (pauses)
                    U-->>RT: approve / reject
                else deny
                    PE-->>RT: deny → observed as blocked
                end
            end
        end
        RT->>CK: save checkpoint after each tool step
    end
    RT-->>RS: state (status, answer, tokens, cost)
    RS-->>U: run record
```

## 2. Governance & human approval

Policies map tools to `allow | deny | require_approval`. The gateway enforces
them synchronously *before* a tool executes, so a governed tool can never run
without a human decision — even while the agent is mid-flight:

```mermaid
sequenceDiagram
    participant Agent as AgentRuntime
    participant GW as Gateway
    participant PE as PolicyEngine
    participant AM as ApprovalManager
    participant DB as SQLite
    participant UI as Studio UI

    Agent->>GW: web.search(q)
    GW->>PE: check("web.search")
    PE-->>GW: allow
    GW->>GW: execute → {output}

    Agent->>GW: database.write(INSERT…)
    GW->>PE: check("database.write")
    PE-->>GW: require_approval
    GW-->>Agent: pause
    Agent->>AM: request_and_wait(...)
    AM->>DB: insert approval (pending)
    AM-->>UI: status = waiting_approval
    UI->>AM: POST /approvals/{id}/approve
    AM->>DB: update → approved
    AM-->>Agent: True (wakes the run)
    Agent->>GW: database.write now executes
```

## 3. Observability: flat events → span tree

Emitters (harness, gateway, sandbox) record **flat, ordered events** through an
asynchronous event bus. `TraceBuilder` reconstructs a nested span tree purely
from that stream, so the Trace view is derived data — never a second code path:

```mermaid
flowchart LR
    E1["run.started"] --> BUS
    E2["context.created"] --> BUS
    E3["llm.request"] --> BUS
    E4["llm.response"] --> BUS
    E5["tool.request"] --> BUS
    E6["tool.completed"] --> BUS
    E7["approval.requested"] --> BUS
    E8["approval.decided"] --> BUS
    BUS --> STORE[("EventStore — SQLite,<br/>WAL, sequence ids")]
    STORE --> TB[TraceBuilder]
    TB --> ROOT{{"root span"}}
    ROOT --> C["context ✔"]
    ROOT --> L["llm ✔"]
    ROOT --> T["tool ✔"]
    ROOT --> A["approval ✔"]
```

## 4. Evaluation & A/B experiments

The offline runner feeds a fixed dataset through the same harness and scores
each case on seven normalised dimensions, then compares whole agents:

```mermaid
flowchart LR
    DS["research.json (31 cases)"] --> RUNNER
    SPEC["AgentSpec (id + strategy)"] --> RUNNER
    RUNNER["EvaluationRunner"] --> RES[("case results")]
    RES --> AGG["aggregates 0..1"]
    AGG --> D1[task_success]
    AGG --> D2[tool_selection]
    AGG --> D3[evidence]
    AGG --> D4[policy]
    AGG --> D5[latency]
    AGG --> D6[cost]
    AGG --> D7[steps]
    RUNNER2["run_ab(control, treatment)"] --> AB["A/B report (per-dimension Δ)"]
```

The results are deterministic (mock LLM), so `POST /api/eval/report/eval/run`
re-produces identical reports — evaluation is a first-class, reproducible
artifact, not a one-off script.
