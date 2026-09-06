// Type mirrors of the AgentOS Studio API surface.

export type RunStatus =
  | "pending"
  | "running"
  | "waiting_approval"
  | "completed"
  | "failed"
  | "cancelled"
  | "budget_exceeded";

export type PolicyAction = "allow" | "deny" | "require_approval";
export type ApprovalStatusType = "pending" | "approved" | "rejected";

export interface ToolInfo {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  risk_level: string;
  timeout: number;
  cost: number;
  permission: string[];
  source: string;
  policy: PolicyAction;
}

export interface AgentInfo {
  agent_id: string;
  name: string;
  category: string;
  description: string;
  capabilities: string[];
  suggested_tasks: string[];
  strategy: string;
  plan: string[];
  badge: string;
  governed: boolean;
}

export interface Run {
  run_id: string;
  agent_id: string;
  task: string;
  status: RunStatus;
  error: string | null;
  answer: string | null;
  steps: number;
  input_tokens: number;
  output_tokens: number;
  cost: number;
  created_at: number;
  finished_at: number | null;
}

export interface TimelinePoint {
  day: string;
  runs: number;
}

export interface Stats {
  runs: {
    total: number;
    completed: number;
    success_rate: number;
    by_status: Partial<Record<RunStatus, number>>;
    timeline: TimelinePoint[];
  };
  usage: {
    steps: number;
    cost: number;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  activity: {
    llm_requests: number;
    llm_responses: number;
    tool_calls: number;
    policy_checks: number;
    approval_requests: number;
    sandbox_starts: number;
    checkpoints: number;
  };
  tools: Record<string, number>;
  approvals: Partial<Record<ApprovalStatusType, number>>;
  policies: { count: number; allow: number; deny: number; require_approval: number };
  agents: number;
}

export interface PolicyRule {
  tool: string;
  action: PolicyAction;
  reason: string;
}

export interface Approval {
  id: string;
  run_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  risk_level: string;
  reason: string;
  status: ApprovalStatusType;
  created_at: number;
  decided_at: number | null;
}

export interface TraceEvent {
  id: string;
  run_id: string;
  type: string;
  timestamp: number;
  sequence: number;
  payload: Record<string, unknown>;
}

export interface Span {
  kind: string;
  name: string;
  start: number;
  end: number | null;
  duration_ms: number | null;
  status: string;
  attrs: Record<string, unknown>;
  children: Span[];
}

export interface TraceSummary {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
  llm_calls: number;
  tool_calls: number;
  sandbox_runs: number;
}

export interface Trace {
  root: Span;
  summary: TraceSummary;
}

export type EvalAggregates = Record<string, number>;

export interface EvalReport {
  dataset: string;
  spec: string;
  case_count: number;
  aggregates: EvalAggregates;
  raw: {
    avg_latency_ms: number;
    avg_cost: number;
    avg_steps: number;
    completed: number;
    total: number;
  };
  results: Array<Record<string, unknown>>;
}

export interface AbDelta {
  dimension: string;
  control: number;
  treatment: number;
  delta: number;
}

export interface AbReport {
  dataset: string;
  control: string;
  treatment: string;
  cases: number;
  overall_delta: number;
  improved: number;
  regressed: number;
  deltas: AbDelta[];
}

export interface SandboxResult {
  status: string;
  exit_code: number;
  stdout: string;
  stderr: string;
  duration_ms: number;
  artifacts: string[];
}

export interface EvalReportListItem {
  id: string;
  kind: string;
  present: boolean;
}
