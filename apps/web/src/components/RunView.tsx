import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { Approval, Run, Trace } from "../lib/types";
import { fmtMoney, fmtNumber } from "../lib/format";
import { TraceTree } from "./TraceTree";
import { Button, EmptyState, ErrorState, Loading, Notice, Spinner } from "./ui";

const TERMINAL = new Set(["completed", "failed", "cancelled", "budget_exceeded"]);
/** How many trace fetch attempts to allow once a run has gone terminal before
 *  giving up and showing "trace unavailable" instead of an infinite spinner. */
const MAX_TRACE_ATTEMPTS = 6;

type TraceState = "loading" | "ready" | "unavailable";

export function RunView({ runId }: { runId: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [traceState, setTraceState] = useState<TraceState>("loading");
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [runError, setRunError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);

  const aliveRef = useRef(true);
  const hasRunRef = useRef(false);
  const traceReadyRef = useRef(false);
  const traceAttemptsRef = useRef(0);
  const latestRun = useRef<Run | null>(null);
  latestRun.current = run;

  const stopPolling = () => {
    const r = latestRun.current;
    if (!r) return false;
    return TERMINAL.has(r.status) && (traceReadyRef.current || traceAttemptsRef.current >= MAX_TRACE_ATTEMPTS);
  };

  const loadTrace = async () => {
    // A just-started run writes trace events fire-and-forget, so the first
    // fetch can legitimately 404 — retried on later poll ticks.
    traceAttemptsRef.current += 1;
    try {
      const t = await api.runTrace(runId);
      if (!aliveRef.current) return;
      setTrace(t);
      traceReadyRef.current = true;
      setTraceState("ready");
    } catch {
      if (!aliveRef.current) return;
      if (traceReadyRef.current) return;
      const r = latestRun.current;
      if (r && TERMINAL.has(r.status) && traceAttemptsRef.current >= MAX_TRACE_ATTEMPTS) {
        setTraceState("unavailable");
      }
      // Non-terminal runs stay "loading" and retry on the next tick.
    }
  };

  const load = async () => {
    if (stopPolling()) return;
    try {
      const r = await api.getRun(runId);
      if (!aliveRef.current) return;
      hasRunRef.current = true;
      setRun(r);
      setRunError(null);
    } catch (e) {
      if (!aliveRef.current) return;
      // A genuine 404 before the run ever appears is fatal; anything else is
      // retried on the next poll tick.
      if (!hasRunRef.current) setRunError(e instanceof Error ? e.message : String(e));
    }
    await loadTrace();
    try {
      const all = await api.approvals();
      if (aliveRef.current) setApprovals(all.filter((a) => a.run_id === runId));
    } catch {
      /* non-fatal */
    }
  };

  useEffect(() => {
    aliveRef.current = true;
    hasRunRef.current = false;
    traceReadyRef.current = false;
    traceAttemptsRef.current = 0;
    setRun(null);
    setTrace(null);
    setTraceState("loading");
    setRunError(null);
    setApprovals([]);
    void load();
    const id = setInterval(() => {
      if (stopPolling()) return;
      void load();
    }, 1200);
    return () => {
      aliveRef.current = false;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const decide = async (id: string, approve: boolean) => {
    setActing(true);
    try {
      if (approve) await api.approve(id);
      else await api.reject(id);
      await load();
    } catch (e) {
      setRunError(e instanceof Error ? e.message : String(e));
    } finally {
      setActing(false);
    }
  };

  if (!run) {
    if (runError) return <ErrorState message={runError} onRetry={() => void load()} />;
    return <Loading label="Loading run…" />;
  }

  const waiting = run.status === "waiting_approval";
  const pendingHere = approvals.filter((a) => a.status === "pending");

  return (
    <div>
      {runError && <Notice tone="error">{runError}</Notice>}

      {waiting && (
        <div className="mb-3 rounded-lg border border-brand/40 bg-brand/10 px-3 py-2.5">
          <div className="flex items-center gap-2 text-sm font-medium text-brandhi">
            <Spinner />
            Waiting for a human decision
          </div>
          {pendingHere.map((a) => (
            <div key={a.id} className="mt-2 rounded-md bg-canvas/50 p-2.5">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-mono text-xs text-fg">{a.tool_name}</div>
                  <pre className="mt-1 max-h-20 overflow-auto whitespace-pre-wrap font-mono text-[11px] text-sub">
                    {JSON.stringify(a.arguments, null, 2)}
                  </pre>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button kind="success" size="sm" disabled={acting} onClick={() => void decide(a.id, true)}>
                    Approve
                  </Button>
                  <Button kind="danger" size="sm" disabled={acting} onClick={() => void decide(a.id, false)}>
                    Reject
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* run meta strip */}
      <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          ["run id", run.run_id],
          ["steps", fmtNumber(run.steps)],
          ["tokens", fmtNumber(run.input_tokens + run.output_tokens)],
          ["cost", fmtMoney(run.cost)],
        ].map(([k, v]) => (
          <div key={k} className="rounded-lg border border-edge bg-panel/70 px-3 py-2">
            <div className="text-[11px] font-medium text-[#8A7C69]">{k}</div>
            <div className="mt-0.5 truncate font-mono text-[13px] text-fg">{v}</div>
          </div>
        ))}
      </div>

      {traceState === "ready" && trace ? (
        <TraceTree trace={trace} />
      ) : traceState === "unavailable" ? (
        <EmptyState
          icon={false}
          title="Trace unavailable"
          hint="This run finished but its span events could not be loaded. It may not have been recorded through the tracing pipeline."
        />
      ) : (
        <div className="flex items-center gap-2 rounded-lg border border-edge bg-panel/40 px-4 py-6 text-sm text-sub">
          <Spinner />
          Building trace…
        </div>
      )}
    </div>
  );
}
