import { useMemo, useState } from "react";
import { api } from "../lib/api";
import type { Approval, RunStatus, Stats, TraceEvent } from "../lib/types";
import { fmtAgo, fmtMoney, fmtNumber, fmtTime } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import { PageHeader, Card, Stat, Button, Loading, ErrorState, EmptyState } from "../components/ui";
import { HBar, TimelineBars } from "../components/charts";

const EVENT_LABEL: Record<string, { label: string; color: string }> = {
  "run.started": { label: "run started", color: "text-gray-300" },
  "run.completed": { label: "run completed", color: "text-emerald-400" },
  "run.failed": { label: "run failed", color: "text-rose-400" },
  "llm.request": { label: "llm request", color: "text-violet-400" },
  "llm.response": { label: "llm response", color: "text-violet-300" },
  "tool.request": { label: "tool called", color: "text-sky-400" },
  "tool.completed": { label: "tool completed", color: "text-sky-300" },
  "policy.checked": { label: "policy checked", color: "text-amber-400" },
  "approval.requested": { label: "approval requested", color: "text-amber-300" },
  "approval.decided": { label: "approval decided", color: "text-emerald-300" },
  "sandbox.started": { label: "sandbox started", color: "text-orange-400" },
  "checkpoint.created": { label: "checkpoint saved", color: "text-gray-400" },
};

function eventMeta(type: string) {
  return EVENT_LABEL[type] ?? { label: type.replace(/\./g, " "), color: "text-gray-400" };
}

const STATUS_ORDER: RunStatus[] = [
  "completed",
  "running",
  "waiting_approval",
  "pending",
  "failed",
  "cancelled",
  "budget_exceeded",
];

export default function OverviewPage() {
  const stats = useFetch<Stats>("/api/stats");
  const approvals = useFetch<Approval[]>("/api/approvals");
  const events = useFetch<TraceEvent[]>("/api/events?limit=60");
  const [acting, setActing] = useState(false);

  const pending = useMemo(
    () => (approvals.data ?? []).filter((a) => a.status === "pending"),
    [approvals.data],
  );

  const decide = async (id: string, approve: boolean) => {
    setActing(true);
    try {
      if (approve) await api.approve(id);
      else await api.reject(id);
      approvals.reload();
      stats.reload();
    } finally {
      setActing(false);
    }
  };

  const s = stats.data;
  const activity = useMemo(() => {
    if (!s) return [];
    const a = s.activity;
    return [
      ["llm requests", a.llm_requests, "text-violet-400"],
      ["tool calls", a.tool_calls, "text-sky-400"],
      ["policy checks", a.policy_checks, "text-amber-400"],
      ["approvals", a.approval_requests, "text-amber-300"],
      ["sandbox runs", a.sandbox_starts, "text-orange-400"],
      ["checkpoints", a.checkpoints, "text-gray-400"],
    ] as const;
  }, [s]);

  const toolList = useMemo(
    () =>
      Object.entries(s?.tools ?? {}).sort((a, b) => b[1] - a[1]),
    [s],
  );
  const toolMax = toolList.length ? toolList[0][1] : 1;

  return (
    <div>
      <PageHeader
        title="Overview"
        desc="Live view of the platform — every number below comes from real runs through the agent runtime."
      />

      {stats.loading ? (
        <Loading />
      ) : stats.error ? (
        <ErrorState message={stats.error} onRetry={stats.reload} />
      ) : s ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat label="Runs" value={fmtNumber(s.runs.total)} accent="sky"
              sub={`${fmtNumber(s.runs.completed)} completed`} />
            <Stat label="Success rate" value={`${s.runs.success_rate}%`} accent="emerald" />
            <Stat label="Tool calls" value={fmtNumber(s.activity.tool_calls)} accent="violet" />
            <Stat label="Tokens" value={fmtNumber(s.usage.total_tokens)} accent="gray"
              sub={`${fmtNumber(s.usage.input_tokens)} in · ${fmtNumber(s.usage.output_tokens)} out`} />
            <Stat label="Est. spend" value={fmtMoney(s.usage.cost)} accent="amber"
              sub="mock provider, real pricing model" />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
            <Card title="Activity" subtitle="Lifecycle events emitted during runs" className="xl:col-span-1">
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                {activity.map(([label, value, color]) => (
                  <div key={label} className="flex items-baseline justify-between gap-2">
                    <span className="text-xs text-gray-500">{label}</span>
                    <span className={`font-mono text-sm ${color}`}>{fmtNumber(value)}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card
              title="Runs over time"
              subtitle="Agent runs per day"
              className="xl:col-span-2"
            >
              <TimelineBars points={s.runs.timeline} />
            </Card>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
            <Card title="Tool usage" subtitle="Calls by tool">
              {toolList.length === 0 && <EmptyState title="No tool calls yet" />}
              {toolList.map(([name, count]) => (
                <HBar key={name} label={name} value={count} max={toolMax} barClass="bg-sky-500" />
              ))}
            </Card>

            <Card
              title="Human approvals"
              subtitle={pending.length ? `${pending.length} waiting` : "queue clear"}
              right={
                <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-300 ring-1 ring-amber-500/30">
                  {pending.length} pending
                </span>
              }
            >
              {approvals.loading ? (
                <Loading />
              ) : pending.length === 0 ? (
                <EmptyState title="No pending approvals" hint="Governed tools (e.g. database.write) appear here when an agent needs your decision." />
              ) : (
                <div className="space-y-2">
                  {pending.map((a) => (
                    <div key={a.id} className="rounded-lg border border-amber-500/20 bg-gray-950/40 p-2.5">
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="truncate font-mono text-xs text-gray-200">{a.tool_name}</span>
                            <span className="rounded bg-amber-500/15 px-1.5 py-px text-[10px] font-medium text-amber-300">
                              {a.risk_level} risk
                            </span>
                          </div>
                          <div className="mt-0.5 text-[10.5px] text-gray-500">
                            run {a.run_id} · {fmtTime(a.created_at)}
                          </div>
                        </div>
                        <div className="flex shrink-0 gap-1.5">
                          <Button kind="success" disabled={acting} onClick={() => void decide(a.id, true)} className="px-2 py-1 text-xs">
                            Approve
                          </Button>
                          <Button kind="danger" disabled={acting} onClick={() => void decide(a.id, false)} className="px-2 py-1 text-xs">
                            Reject
                          </Button>
                        </div>
                      </div>
                      <pre className="mt-1.5 max-h-20 overflow-auto rounded bg-gray-900/70 p-1.5 whitespace-pre-wrap font-mono text-[10px] text-gray-500">
                        {JSON.stringify(a.arguments, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Card title="Run status" subtitle="Distribution across the fleet">
              <div className="grid grid-cols-2 gap-2">
                {STATUS_ORDER.filter((st) => s.runs.by_status[st]).map((st) => (
                  <div key={st} className="flex items-center justify-between rounded-lg bg-gray-950/40 px-3 py-2">
                    <span className="text-xs capitalize text-gray-400">{st.replace("_", " ")}</span>
                    <span className="font-mono text-sm text-gray-100">{fmtNumber(s.runs.by_status[st] ?? 0)}</span>
                  </div>
                ))}
                {!STATUS_ORDER.some((st) => s.runs.by_status[st]) && (
                  <EmptyState title="No runs yet" hint="Launch one from the Agents page." />
                )}
              </div>
            </Card>

            <Card title="Recent events" subtitle="Live trace feed">
              {events.loading ? (
                <Loading />
              ) : (events.data ?? []).length === 0 ? (
                <EmptyState title="No events yet" />
              ) : (
                <ul className="divide-y divide-gray-800/60">
                  {(events.data ?? []).slice(0, 14).map((e) => {
                    const meta = eventMeta(e.type);
                    return (
                      <li key={e.id} className="flex items-center gap-2 py-1.5 text-xs">
                        <span className={`w-28 shrink-0 font-mono ${meta.color}`}>{meta.label}</span>
                        <span className="truncate font-mono text-gray-600">{e.run_id}</span>
                        <span className="ml-auto shrink-0 text-[10px] text-gray-600">{fmtAgo(e.timestamp)}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
