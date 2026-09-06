import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../lib/api";
import type { Approval, RunStatus, Stats, TraceEvent } from "../lib/types";
import { fmtAgo, fmtMoney, fmtNumber, fmtTime } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import {
  PageHeader,
  Card,
  Button,
  Loading,
  ErrorState,
  EmptyState,
  Skeleton,
  StatusBadge,
  Chip,
  cx,
} from "../components/ui";
import type { Tone } from "../components/ui";
import { HBar, TimelineBars } from "../components/charts";

/* Warm-organic event legend: ochre = model I/O, olive = tool work + success,
 * terracotta = guardrails / human decisions, rust = failure, sand = lifecycle. */
const EVENT_META: Record<string, { label: string; tone: Tone }> = {
  "run.prepared": { label: "run prepared", tone: "neutral" },
  "run.started": { label: "run started", tone: "neutral" },
  "run.completed": { label: "run completed", tone: "olive" },
  "run_finalized": { label: "run finalized", tone: "neutral" },
  "context.created": { label: "context built", tone: "neutral" },
  "llm.request": { label: "llm request", tone: "ochre" },
  "llm.response": { label: "llm response", tone: "ochre" },
  "tool.started": { label: "tool started", tone: "olive" },
  "tool.request": { label: "tool requested", tone: "olive" },
  "tool.completed": { label: "tool completed", tone: "olive" },
  "tool.failed": { label: "tool failed", tone: "rust" },
  "observation": { label: "observation", tone: "neutral" },
  "policy.checked": { label: "policy checked", tone: "terra" },
  "approval.requested": { label: "approval requested", tone: "terra" },
  "approval.decided": { label: "approval decided", tone: "olive" },
  "checkpoint.created": { label: "checkpoint saved", tone: "neutral" },
};

function eventMeta(type: string): { label: string; tone: Tone } {
  return EVENT_META[type] ?? { label: type.replace(/[._]/g, " "), tone: "neutral" };
}

const STATUS_ORDER: RunStatus[] = [
  "running",
  "waiting_approval",
  "pending",
  "completed",
  "failed",
  "cancelled",
  "budget_exceeded",
];

/* Warm muted text used on the sand hero band. */
const bandLabel = "text-xs font-medium text-[#8A7C69]";
const bandSub = "mt-1.5 text-xs leading-snug text-[#8A7C69]";

function OverviewSkeleton() {
  return (
    <>
      <div className="overflow-hidden rounded-lg border border-edge bg-sand/60 shadow-card">
        <div className="grid grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className={cx("px-5 py-4", i > 0 && "border-l border-[#DECBAE]/80")}>
              <Skeleton className="h-3 w-16" />
              <Skeleton className="mt-2.5 h-7 w-14" />
              <Skeleton className="mt-2.5 h-3 w-24" />
            </div>
          ))}
        </div>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <div className="rounded-lg border border-edge bg-panel p-4 shadow-card">
          <Skeleton className="h-4 w-28" />
          <div className="mt-6 flex h-40 items-end gap-2">
            {Array.from({ length: 12 }, (_, i) => (
              <Skeleton key={i} className="flex-1 rounded-md" style={{ height: `${10 + ((i * 19) % 90)}px` }} />
            ))}
          </div>
        </div>
        <div className="space-y-4">
          <div className="rounded-lg border border-edge bg-panel p-4 shadow-card">
            <Skeleton className="h-4 w-24" />
            <div className="mt-4 space-y-3">
              {Array.from({ length: 6 }, (_, i) => (
                <Skeleton key={i} className="h-3.5 w-full" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

/** A single metric in the sand hero band. Label + big value + optional caption. */
function Metric({
  label,
  value,
  sub,
  className,
  valueClass,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  className?: string;
  valueClass?: string;
}) {
  return (
    <div className={cx("px-5 py-4", className)}>
      <div className={bandLabel}>{label}</div>
      <div
        className={cx(
          "mt-1 text-[25px] font-semibold leading-none tracking-tight tabular-nums",
          valueClass ?? "text-ink",
        )}
      >
        {value}
      </div>
      {sub && <div className={bandSub}>{sub}</div>}
    </div>
  );
}

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
      ["llm requests", a.llm_requests],
      ["tool calls", a.tool_calls],
      ["policy checks", a.policy_checks],
      ["approvals", a.approval_requests],
      ["checkpoints", a.checkpoints],
      ["sandbox runs", a.sandbox_starts],
    ] as const;
  }, [s]);

  const toolList = useMemo(
    () => Object.entries(s?.tools ?? {}).sort((a, b) => b[1] - a[1]),
    [s],
  );
  const toolMax = toolList.length ? toolList[0][1] : 1;

  const byStatus = useMemo(
    () => STATUS_ORDER.filter((st) => (s?.runs.by_status[st] ?? 0) > 0),
    [s],
  );

  return (
    <div>
      <PageHeader
        title="Overview"
        desc="Every number below comes from real runs through the agent runtime — deterministic mock LLM, reproducible end to end."
      />

      {stats.loading ? (
        <OverviewSkeleton />
      ) : stats.error ? (
        <ErrorState message={stats.error} onRetry={stats.reload} />
      ) : s ? (
        <>
          {/* Sand hero band — one warm panel, hairline-divided metrics. */}
          <div className="overflow-hidden rounded-lg border border-edge bg-sand/60 shadow-card">
            <div className="grid grid-cols-2 lg:grid-cols-5">
              <Metric
                label="Runs"
                value={fmtNumber(s.runs.total)}
                valueClass="text-brand"
                sub={`${fmtNumber(s.runs.completed)} completed`}
              />
              <Metric className="border-l border-[#DECBAE]/80" label="Success rate" value={`${s.runs.success_rate}%`} />
              <Metric className="border-l border-[#DECBAE]/80" label="Tool calls" value={fmtNumber(s.activity.tool_calls)} />
              <Metric
                className="border-l border-[#DECBAE]/80"
                label="Tokens"
                value={fmtNumber(s.usage.total_tokens)}
                sub={`${fmtNumber(s.usage.input_tokens)} in · ${fmtNumber(s.usage.output_tokens)} out`}
              />
              <Metric className="border-l border-[#DECBAE]/80" label="Est. spend" value={fmtMoney(s.usage.cost)} sub="at mock pricing" />
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
            {/* Left: the story of recent runs. */}
            <div className="min-w-0 space-y-4">
              <Card title="Runs over time" subtitle="Agent runs per day">
                <TimelineBars points={s.runs.timeline} />
              </Card>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <Card title="Tool usage" subtitle="Calls by tool">
                  {toolList.length === 0 ? (
                    <EmptyState title="No tool calls yet" />
                  ) : (
                    <div className="py-1">
                      {toolList.map(([name, count]) => (
                        <HBar key={name} label={name} value={count} max={toolMax} />
                      ))}
                    </div>
                  )}
                </Card>

                <Card title="Run status" subtitle="Distribution across the fleet">
                  {byStatus.length === 0 ? (
                    <EmptyState title="No runs yet" hint="Launch one from the Agents page." />
                  ) : (
                    <div className="divide-y divide-edge/80">
                      {byStatus.map((st) => (
                        <div key={st} className="flex items-center justify-between py-1.5">
                          <StatusBadge status={st} />
                          <span className="font-mono text-xs text-ink/80 tabular-nums">
                            {fmtNumber(s.runs.by_status[st] ?? 0)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            </div>

            {/* Right: decisions + activity + live feed. */}
            <div className="space-y-4">
              <Card
                title="Human approvals"
                subtitle={pending.length ? "Waiting on your decision" : "Queue clear"}
              >
                {approvals.loading ? (
                  <Loading />
                ) : pending.length === 0 ? (
                  <div className="rounded-md border border-clay/70 bg-sand/40 px-3 py-2.5 text-xs leading-relaxed text-[#8A7C69]">
                    Governed tools (e.g. <code className="font-mono">database.write</code>) pause a run here
                    for a decision.
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {pending.map((a) => (
                      <div key={a.id} className="rounded-lg border border-brand/40 bg-brand/8 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="font-mono text-xs font-medium text-ink">{a.tool_name}</div>
                            <div className="mt-0.5 truncate text-[11px] text-[#8A7C69]">
                              run {a.run_id} · {fmtTime(a.created_at)}
                            </div>
                          </div>
                          <div className="flex shrink-0 gap-1.5">
                            <Button kind="success" size="sm" disabled={acting} onClick={() => void decide(a.id, true)}>
                              Approve
                            </Button>
                            <Button kind="danger" size="sm" disabled={acting} onClick={() => void decide(a.id, false)}>
                              Reject
                            </Button>
                          </div>
                        </div>
                        <pre className="mt-2 max-h-24 overflow-auto whitespace-pre-wrap rounded-md bg-panel px-2.5 py-2 font-mono text-[11px] leading-relaxed text-[#6E624F] ring-1 ring-inset ring-clay/60">
                          {JSON.stringify(a.arguments, null, 2)}
                        </pre>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              <Card title="Activity" subtitle="Lifecycle events emitted during runs">
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 py-1">
                  {activity.map(([label, value]) => (
                    <div key={label} className="flex items-baseline justify-between gap-2 border-b border-edge/70 py-1">
                      <span className="text-xs text-[#8A7C69]">{label}</span>
                      <span className="font-mono text-[13px] text-ink tabular-nums">{fmtNumber(value)}</span>
                    </div>
                  ))}
                </div>
              </Card>

              <Card title="Recent events" subtitle="Live trace feed" pad={false}>
                {events.loading ? (
                  <div className="p-4"><Loading /></div>
                ) : (events.data ?? []).length === 0 ? (
                  <EmptyState title="No events yet" />
                ) : (
                  <ul className="divide-y divide-edge/80">
                    {(events.data ?? []).slice(0, 12).map((e) => {
                      const meta = eventMeta(e.type);
                      return (
                        <li key={e.id} className="flex items-center gap-2.5 px-4 py-[7px]">
                          <Chip tone={meta.tone} label={meta.label} />
                          <span className="min-w-0 truncate font-mono text-[11px] text-[#A0927C]">{e.run_id}</span>
                          <span className="ml-auto shrink-0 text-[11px] text-[#A0927C] tabular-nums">
                            {fmtAgo(e.timestamp)}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </Card>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
