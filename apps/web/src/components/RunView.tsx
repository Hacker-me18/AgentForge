import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { Approval, Run, Trace } from "../lib/types";
import { fmtMoney, fmtNumber } from "../lib/format";
import { TraceTree } from "./TraceTree";
import { Button, ErrorState, Loading, Spinner } from "./ui";

const TERMINAL = new Set(["completed", "failed", "cancelled", "budget_exceeded"]);

export function RunView({ runId }: { runId: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);

  const aliveRef = useRef(true);
  const hasRun = useRef(false);
  const latestRun = useRef<Run | null>(null);
  latestRun.current = run;

  const load = async () => {
    // The run record is authoritative: a genuine 404 surfaces an error. But a
    // just-started run's trace events are written fire-and-forget, so its first
    // fetch can legitimately 404 — swallow that and let the poll retry.
    try {
      const r = await api.getRun(runId);
      if (!aliveRef.current) return;
      hasRun.current = true;
      setRun(r);
      setError(null);
    } catch (e) {
      if (!aliveRef.current) return;
      if (!hasRun.current) setError(e instanceof Error ? e.message : String(e));
    }
    try {
      const t = await api.runTrace(runId);
      if (aliveRef.current) setTrace(t);
    } catch {
      /* retried on next poll tick */
    }
    try {
      const all = await api.approvals();
      if (aliveRef.current) setApprovals(all.filter((a) => a.run_id === runId));
    } catch {
      /* non-fatal */
    }
  };

  useEffect(() => {
    aliveRef.current = true;
    hasRun.current = false;
    setRun(null);
    setTrace(null);
    setError(null);
    void load();
    const id = setInterval(() => {
      const current = latestRun.current;
      if (!current || TERMINAL.has(current.status)) return;
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
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setActing(false);
    }
  };

  if (!run || !trace) {
    if (error) return <ErrorState message={error} onRetry={() => void load()} />;
    return <Loading label="Loading run trace…" />;
  }

  const waiting = run.status === "waiting_approval";
  const pendingHere = approvals.filter((a) => a.status === "pending");

  return (
    <div>
      {error && (
        <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-300">
          {error}
        </div>
      )}

      {waiting && (
        <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2.5">
          <div className="flex items-center gap-2 text-sm font-medium text-amber-300">
            <Spinner />
            Waiting for a human decision
          </div>
          {pendingHere.map((a) => (
            <div key={a.id} className="mt-2 rounded-md bg-gray-900/70 p-2.5">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-mono text-xs text-gray-200">{a.tool_name}</div>
                  <pre className="mt-1 max-h-20 overflow-auto whitespace-pre-wrap font-mono text-[10.5px] text-gray-500">
                    {JSON.stringify(a.arguments, null, 2)}
                  </pre>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button kind="success" disabled={acting} onClick={() => void decide(a.id, true)}>
                    Approve
                  </Button>
                  <Button kind="danger" disabled={acting} onClick={() => void decide(a.id, false)}>
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
          <div key={k} className="rounded-lg border border-gray-800 bg-gray-900/60 px-3 py-2">
            <div className="text-[10px] font-medium uppercase tracking-wide text-gray-600">{k}</div>
            <div className="mt-0.5 truncate font-mono text-sm text-gray-100">{v}</div>
          </div>
        ))}
      </div>

      <TraceTree trace={trace} />
    </div>
  );
}
