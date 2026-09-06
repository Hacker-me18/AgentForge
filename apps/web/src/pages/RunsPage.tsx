import { useMemo, useState } from "react";
import type { Run, RunStatus } from "../lib/types";
import { fmtAgo, fmtCost, fmtNumber } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import { Drawer } from "../components/Drawer";
import { RunView } from "../components/RunView";
import { PageHeader, StatusBadge, Loading, ErrorState, EmptyState, cx } from "../components/ui";

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
            className="w-64 rounded-lg border border-gray-700 bg-gray-900 px-3 py-1.5 text-sm text-gray-200 placeholder:text-gray-600 focus:border-sky-500 focus:outline-none"
          />
        }
      />

      <div className="mb-3 flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cx(
              "rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors",
              filter === f
                ? "bg-gray-200 text-gray-900"
                : "bg-gray-800/60 text-gray-400 hover:bg-gray-800 hover:text-gray-200",
            )}
          >
            {f === "all" ? "all" : f.replace("_", " ")}
            <span className="ml-1.5 opacity-60">{f === "all" ? runs.data?.length ?? 0 : counts.get(f) ?? 0}</span>
          </button>
        ))}
      </div>

      {runs.loading ? (
        <Loading />
      ) : runs.error ? (
        <ErrorState message={runs.error} onRetry={runs.reload} />
      ) : filtered.length === 0 ? (
        <EmptyState title="No runs match" hint="Adjust the filter or start a run from the Agents page." />
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-900 text-[11px] uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Run</th>
                <th className="px-3 py-2 font-medium">Agent</th>
                <th className="px-3 py-2 font-medium">Task / Answer</th>
                <th className="px-3 py-2 text-right font-medium">Steps</th>
                <th className="px-3 py-2 text-right font-medium">Cost</th>
                <th className="px-3 py-2 text-right font-medium">When</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/70 bg-gray-900/40">
              {filtered.map((run) => (
                <tr
                  key={run.run_id}
                  onClick={() => setActive(run)}
                  className="cursor-pointer transition-colors hover:bg-gray-800/50"
                >
                  <td className="px-3 py-2">
                    <StatusBadge status={run.status} />
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-gray-400">{run.run_id}</td>
                  <td className="px-3 py-2 font-mono text-xs text-gray-300">{run.agent_id}</td>
                  <td className="max-w-md px-3 py-2">
                    <div className="truncate text-xs text-gray-300">{run.task}</div>
                    {run.answer && (
                      <div className="mt-0.5 line-clamp-1 text-xs text-gray-600">{run.answer}</div>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs text-gray-400">
                    {fmtNumber(run.steps)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs text-emerald-400">
                    {fmtCost(run.cost)}
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-gray-500">
                    {fmtAgo(run.created_at)}
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
