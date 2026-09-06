import { useMemo, useState } from "react";
import { ChevronRight } from "lucide-react";
import type { Run, RunStatus } from "../lib/types";
import { fmtAgo, fmtCost, fmtNumber } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import { Drawer } from "../components/Drawer";
import { RunView } from "../components/RunView";
import {
  PageHeader,
  StatusBadge,
  TableSkeleton,
  ErrorState,
  EmptyState,
  inputCls,
  cx,
} from "../components/ui";

const FILTERS: Array<RunStatus | "all"> = [
  "all",
  "completed",
  "running",
  "waiting_approval",
  "failed",
  "cancelled",
];

export default function RunsPage() {
  const runs = useFetch<Run[]>("/api/runs?limit=200");
  const [active, setActive] = useState<Run | null>(null);
  const [filter, setFilter] = useState<RunStatus | "all">("all");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    let list = runs.data ?? [];
    if (filter !== "all") list = list.filter((r) => r.status === filter);
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (r) =>
          r.task.toLowerCase().includes(q) ||
          r.run_id.toLowerCase().includes(q) ||
          r.agent_id.toLowerCase().includes(q),
      );
    }
    return list;
  }, [runs.data, filter, query]);

  const counts = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of runs.data ?? []) m.set(r.status, (m.get(r.status) ?? 0) + 1);
    return m;
  }, [runs.data]);

  return (
    <div>
      <PageHeader
        title="Runs"
        desc="Every execution through the harness — its tool calls, tokens, cost and final answer. Open a row to inspect the full trace."
        actions={
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search task / run id…"
            aria-label="Search runs"
            className={cx(inputCls, "w-64")}
          />
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter by status">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            aria-pressed={filter === f}
            className={cx(
              "inline-flex h-6 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium transition-colors",
              filter === f
                ? "bg-[#E1D3BE] text-ink ring-1 ring-inset ring-clay/80"
                : "text-[#7C7160] hover:bg-sand/70 hover:text-ink",
            )}
          >
            {f === "all" ? "all" : f.replace("_", " ")}
            <span className={filter === f ? "opacity-60" : "opacity-70"}>
              {f === "all" ? runs.data?.length ?? 0 : counts.get(f) ?? 0}
            </span>
          </button>
        ))}
      </div>

      {runs.loading ? (
        <TableSkeleton rows={8} />
      ) : runs.error ? (
        <ErrorState message={runs.error} onRetry={runs.reload} />
      ) : filtered.length === 0 ? (
        <EmptyState title="No runs match" hint="Adjust the filter or start a run from the Agents page." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-edge">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-edge text-[11px] font-medium text-[#8A7C69]">
                <th scope="col" className="px-3 py-2 font-medium">Status</th>
                <th scope="col" className="px-3 py-2 font-medium">Run</th>
                <th scope="col" className="px-3 py-2 font-medium">Agent</th>
                <th scope="col" className="px-3 py-2 font-medium">Task / Answer</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">Steps</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">Cost</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">When</th>
                <th scope="col" className="w-8 px-2 py-2"><span className="sr-only">Open</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-edge/60 bg-panel/30">
              {filtered.map((run) => (
                <tr
                  key={run.run_id}
                  onClick={() => setActive(run)}
                  className="cursor-pointer transition-colors hover:bg-raised/40"
                >
                  <td className="px-3 py-2"><StatusBadge status={run.status} /></td>
                  <td className="px-3 py-2 font-mono text-xs text-sub">{run.run_id}</td>
                  <td className="px-3 py-2 font-mono text-xs text-sub">{run.agent_id}</td>
                  <td className="max-w-md px-3 py-2">
                    <div className="truncate text-xs text-fg">{run.task}</div>
                    {run.answer && (
                      <div className="mt-0.5 line-clamp-1 text-xs text-faint">{run.answer}</div>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs text-fg">{fmtNumber(run.steps)}</td>
                  <td className="px-3 py-2 text-right font-mono text-xs text-fg">{fmtCost(run.cost)}</td>
                  <td className="px-3 py-2 text-right text-xs text-faint">{fmtAgo(run.created_at)}</td>
                  <td className="px-2 py-2 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setActive(run);
                      }}
                      aria-label={`Open run ${run.run_id}`}
                      className="inline-flex h-6 w-6 items-center justify-center rounded-md text-faint transition-colors hover:bg-raised hover:text-ink"
                    >
                      <ChevronRight aria-hidden className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Drawer
        open={active !== null}
        onClose={() => setActive(null)}
        title={active ? `Run ${active.run_id}` : ""}
        subtitle={active ? active.task : ""}
      >
        {active && <RunView key={active.run_id} runId={active.run_id} />}
      </Drawer>
    </div>
  );
}
