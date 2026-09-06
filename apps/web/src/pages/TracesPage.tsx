import { useEffect, useMemo, useState } from "react";
import type { Run } from "../lib/types";
import { fmtCost, fmtNumber } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import { RunView } from "../components/RunView";
import { PageHeader, StatusBadge, Loading, ErrorState, EmptyState, cx } from "../components/ui";

export default function TracesPage() {
  const runs = useFetch<Run[]>("/api/runs?limit=200");
  const [selected, setSelected] = useState<Run | null>(null);

  useEffect(() => {
    if (!selected && runs.data && runs.data.length) setSelected(runs.data[0]);
  }, [runs.data, selected]);

  const sorted = useMemo(() => [...(runs.data ?? [])], [runs.data]);

  return (
    <div>
      <PageHeader
        title="Traces"
        desc="Reconstructed span trees from the flat event stream of each run — LLM calls, tool executions, policy checks and the human-approval gate, with timing."
      />

      {runs.loading ? (
        <Loading />
      ) : runs.error ? (
        <ErrorState message={runs.error} onRetry={runs.reload} />
      ) : sorted.length === 0 ? (
        <EmptyState title="No traces yet" hint="Traces appear once a run has been executed." />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
          <div className="h-fit overflow-hidden rounded-xl border border-gray-800">
            <div className="border-b border-gray-800 bg-gray-900 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
              Runs
            </div>
            <ul className="max-h-[70vh] divide-y divide-gray-800/60 overflow-y-auto bg-gray-900/40">
              {sorted.map((run) => (
                <li key={run.run_id}>
                  <button
                    onClick={() => setSelected(run)}
                    className={cx(
                      "flex w-full items-start gap-2 px-3 py-2 text-left transition-colors hover:bg-gray-800/50",
                      selected?.run_id === run.run_id && "bg-gray-800/70",
                    )}
                  >
                    <span className="mt-1 shrink-0">
                      <StatusBadge status={run.status} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-mono text-[11px] text-gray-300">{run.run_id}</span>
                      <span className="mt-0.5 line-clamp-2 block text-xs text-gray-500">{run.task}</span>
                      <span className="mt-1 flex gap-3 font-mono text-[10px] text-gray-600">
                        <span>{run.agent_id}</span>
                        <span>{fmtNumber(run.steps)} steps</span>
                        <span className="text-emerald-500/70">{fmtCost(run.cost)}</span>
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div className="min-w-0">
            {selected ? (
              <RunView key={selected.run_id} runId={selected.run_id} />
            ) : (
              <EmptyState title="Select a run" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
