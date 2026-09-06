// Minimal typed HTTP client for the AgentOS Studio API (served same-origin
// through the Vite dev proxy, which forwards /api to :8000).

import type {
  AbReport,
  AgentInfo,
  Approval,
  EvalReport,
  EvalReportListItem,
  PolicyRule,
  Run,
  RunStatus,
  SandboxResult,
  Stats,
  ToolInfo,
  Trace,
  TraceEvent,
} from "./types";

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const data = (await res.json()) as { detail?: string };
      if (data.detail) detail = data.detail;
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

const get = <T>(path: string) => request<T>("GET", path);
const post = <T>(path: string, body?: unknown) => request<T>("POST", path, body);
const put = <T>(path: string, body?: unknown) => request<T>("PUT", path, body);

export const api = {
  // Overview / stats
  stats: () => get<Stats>("/api/stats"),

  // Runs
  listRuns: () => get<Run[]>("/api/runs?limit=100"),
  getRun: (runId: string) => get<Run>(`/api/runs/${runId}`),
  startRun: (task: string, agentId: string) =>
    post<Run>("/api/runs", { task, agent_id: agentId, max_steps: 12 }),
  cancelRun: (runId: string) => post<Run>(`/api/runs/${runId}/cancel`),
  runEvents: (runId: string) => get<TraceEvent[]>(`/api/runs/${runId}/events`),
  runTrace: (runId: string) => get<Trace>(`/api/runs/${runId}/trace`),
  recentEvents: () => get<TraceEvent[]>("/api/events?limit=50"),

  // Catalog
  tools: () => get<ToolInfo[]>("/api/tools"),
  agents: () => get<AgentInfo[]>("/api/agents"),

  // Policies
  policies: () => get<PolicyRule[]>("/api/policies"),
  upsertPolicy: (rule: PolicyRule) => put<PolicyRule>("/api/policies", rule),

  // Approvals
  approvals: () => get<Approval[]>("/api/approvals"),
  approve: (id: string) => post<Approval>(`/api/approvals/${id}/approve`),
  reject: (id: string) => post<Approval>(`/api/approvals/${id}/reject`),

  // Sandbox
  sandboxRun: (code: string, timeoutS = 10) =>
    post<SandboxResult>("/api/sandbox/run", { code, timeout_s: timeoutS }),

  // Evaluation
  evalReports: () => get<EvalReportListItem[]>("/api/eval/reports"),
  evalReport: () => get<EvalReport>("/api/eval/report/eval"),
  rerunEvalReport: () => post<EvalReport>("/api/eval/report/eval/run"),
  abReport: () => get<AbReport>("/api/eval/report/ab"),
  rerunAbReport: () => post<AbReport>("/api/eval/report/ab/run"),
};

export type { RunStatus };
