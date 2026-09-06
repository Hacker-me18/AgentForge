import type { ReactNode } from "react";
import type { AgentInfo, EvalReportListItem, PolicyRule, Stats, ToolInfo } from "../lib/types";
import { fmtNumber } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import { PageHeader, Card, Button, Loading, Spinner, cx } from "../components/ui";

const COMPONENTS: Array<{ name: string; path: string; blurb: string }> = [
  { name: "Runtime core", path: "packages/runtime", blurb: "AgentState · harness loop · checkpointing · budget" },
  { name: "Context engine", path: "packages/context", blurb: "System-prompt assembly & context extras" },
  { name: "Tool registry", path: "packages/tools", blurb: "Built-in tools + MCP client/server + gateway envelope" },
  { name: "Sandbox", path: "packages/sandbox", blurb: "Docker executor with network/cpu/mem limits" },
  { name: "Policy & approvals", path: "packages/policy", blurb: "allow · deny · require_approval + human queue" },
  { name: "Tracing", path: "packages/tracing", blurb: "Event bus → flat store → span-tree builder" },
  { name: "Evaluation", path: "packages/evaluation", blurb: "Offline 7-dimension scoring + A/B experiments" },
  { name: "LLM providers", path: "packages/llm", blurb: "Mock (deterministic) · DeepSeek · OpenAI" },
  { name: "Studio API", path: "apps/api", blurb: "FastAPI + aiosqlite, no ORM" },
  { name: "Studio Web", path: "apps/web", blurb: "React 18 + TS + Tailwind dashboard" },
];

const ENV: Array<[string, string]> = [
  ["AGENTOS_DATABASE_URL", "sqlite+aiosqlite:///./data/agentos.db"],
  ["AGENTOS_LLM_PROVIDER", "mock  (mock | deepseek | openai | openai_compatible)"],
  ["AGENTOS_LLM_MODEL", "mock-model  (e.g. deepseek-chat)"],
  ["AGENTOS_LOG_LEVEL", "INFO"],
  ["DEEPSEEK_API_KEY / OPENAI_API_KEY", "set when provider ≠ mock"],
];

const COMMANDS: Array<[string, string]> = [
  ["Install", "pip install -e . && cd apps/web && npm install"],
  ["Seed demo data", "python scripts/seed_demo.py"],
  ["Run API", "uvicorn apps.api.main:app --port 8000"],
  ["Run web", "npm run dev   (apps/web, http://localhost:3000)"],
  ["Tests", "pytest -q   (51 tests, incl. docker-sandbox) · ruff · mypy"],
];

function Check({ label, ok, note }: { label: string; ok: boolean; note?: ReactNode }) {
  return (
    <div className="flex items-center gap-2.5 py-1.5 text-xs">
      <span
        className={cx(
          "flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold text-gray-950",
          ok ? "bg-emerald-400" : "bg-rose-400",
        )}
      >
        {ok ? "✓" : "✕"}
      </span>
      <span className="w-40 shrink-0 text-gray-300">{label}</span>
      <span className="truncate font-mono text-gray-600">{note}</span>
    </div>
  );
}

export default function SettingsPage() {
  const stats = useFetch<Stats>("/api/stats");
  const tools = useFetch<ToolInfo[]>("/api/tools");
  const agents = useFetch<AgentInfo[]>("/api/agents");
  const policies = useFetch<PolicyRule[]>("/api/policies");
  const reports = useFetch<EvalReportListItem[]>("/api/eval/reports");
  const health = useFetch<{ status: string }>("/api/health");

  const ready = !stats.loading;
  return (
    <div>
      <PageHeader
        title="Settings"
        desc="Platform diagnostics and project information for the AgentOS Studio monorepo."
      />

      <div className="mb-4">
        <h2 className="text-sm font-semibold text-gray-300">Environment</h2>
        {!ready ? (
          <div className="mt-3"><Loading /></div>
        ) : (
          <div className="mt-2 rounded-xl border border-gray-800 bg-gray-900/60 px-4 py-3">
            <Check label="API reachable" ok={health.data?.status === "ok"} note={health.error ?? "http://localhost:8000"} />
            <Check label="Database" ok={!stats.error} note={`${stats.data?.runs.total ?? 0} runs · sqlite (aiosqlite)`} />
            <Check label="Agents catalog" ok={(agents.data ?? []).length > 0} note={`${agents.data?.length ?? 0} agents`} />
            <Check label="Tool registry" ok={(tools.data ?? []).length > 0} note={`${tools.data?.length ?? 0} tools`} />
            <Check label="Policy rules" ok={(policies.data ?? []).length > 0} note={`${policies.data?.length ?? 0} rules`} />
            <Check
              label="Evaluation reports"
              ok={(reports.data ?? []).some((r) => r.present)}
              note={reports.data?.map((r) => `${r.id}:${r.present ? "on" : "off"}`).join(" · ")}
            />
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Components" subtitle="Monorepo layout — each capability is an isolated package">
          <ul className="divide-y divide-gray-800/60">
            {COMPONENTS.map((c) => (
              <li key={c.path} className="flex items-start gap-3 py-1.5">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-gray-800 text-[9px] font-bold text-gray-300">
                  <svg viewBox="0 0 20 20" className="h-3 w-3" fill="currentColor">
                    <path d="M2 4h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-7l-1 2H6l-1-2H2a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zm1 2v7h14V6H3z" />
                  </svg>
                </span>
                <div className="min-w-0">
                  <div className="text-xs font-medium text-gray-200">{c.name}</div>
                  <div className="truncate font-mono text-[10px] text-gray-600">{c.path}</div>
                </div>
                <div className="ml-auto text-right text-[11px] text-gray-500">{c.blurb}</div>
              </li>
            ))}
          </ul>
        </Card>

        <div className="space-y-4">
          <Card title="Runbook" subtitle="From a clean checkout to this dashboard">
            <ol className="space-y-1.5">
              {COMMANDS.map(([label, cmd]) => (
                <li key={label} className="flex items-center gap-3 text-xs">
                  <span className="w-14 shrink-0 font-medium text-gray-500">{label}</span>
                  <code className="flex-1 truncate rounded bg-gray-950/80 px-2 py-1 font-mono text-[11px] text-emerald-300/90">
                    {cmd}
                  </code>
                </li>
              ))}
            </ol>
          </Card>

          <Card title="Configuration" subtitle="All settings are env-driven with sane defaults">
            <ul className="divide-y divide-gray-800/60">
              {ENV.map(([k, v]) => (
                <li key={k} className="py-1.5 text-xs">
                  <div className="font-mono text-gray-300">{k}</div>
                  <div className="truncate font-mono text-[10.5px] text-gray-600">{v}</div>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Live totals" subtitle="Fetched from the API just now">
            {stats.data ? (
              <div className="grid grid-cols-4 gap-2 text-center">
                {[
                  ["runs", fmtNumber(stats.data.runs.total)],
                  ["tool calls", fmtNumber(stats.data.activity.tool_calls)],
                  ["tokens", fmtNumber(stats.data.usage.total_tokens)],
                  ["spend", `$${stats.data.usage.cost.toFixed(6)}`],
                ].map(([k, v]) => (
                  <div key={String(k)} className="rounded-lg bg-gray-950/60 px-2 py-2.5">
                    <div className="text-[10px] uppercase tracking-wide text-gray-600">{k}</div>
                    <div className="mt-0.5 truncate font-mono text-sm text-gray-100">{v}</div>
                  </div>
                ))}
              </div>
            ) : stats.loading ? (
              <div className="flex items-center gap-2 text-xs text-gray-500"><Spinner /> loading…</div>
            ) : (
              <Button onClick={stats.reload}>Reload stats</Button>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
