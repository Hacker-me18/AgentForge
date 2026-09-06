import { useState } from "react";
import { api } from "../lib/api";
import type { AbReport } from "../lib/types";
import { useFetch } from "../lib/useFetch";
import { PageHeader, Card, Button, Loading, ErrorState, EmptyState, Spinner } from "../components/ui";
import { CompareBar } from "../components/charts";

export default function ExperimentsPage() {
  const fetch = useFetch<AbReport>("/api/eval/report/ab");
  const [data, setData] = useState<AbReport | null>(null);
  const [running, setRunning] = useState(false);

  const ab = data ?? fetch.data;

  const rerun = async () => {
    setRunning(true);
    try {
      setData(await api.rerunAbReport());
    } catch (e) {
      window.alert(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const loading = fetch.loading && !ab;

  return (
    <div>
      <PageHeader
        title="Experiments"
        desc="A/B the agent routing strategy offline: the routing agent (v1.0) versus a plain echo baseline (v1.1) across the same research dataset. The harness scores both arms so you can ship the version that actually works."
        actions={
          <Button onClick={() => void rerun()} disabled={running}>
            {running ? (
              <>
                <Spinner /> Running…
              </>
            ) : (
              "Re-run experiment"
            )}
          </Button>
        }
      />

      {loading ? (
        <Loading />
      ) : fetch.error && !ab ? (
        <ErrorState message={fetch.error} onRetry={fetch.reload} />
      ) : ab ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <div className="rounded-xl border border-gray-800 bg-gray-900/60 px-4 py-3.5">
              <div className="text-[11px] font-medium uppercase tracking-wide text-gray-500">Cases</div>
              <div className="mt-1 text-2xl font-semibold text-gray-50">{ab.cases}</div>
              <div className="text-xs text-gray-500">per arm · {ab.dataset} dataset</div>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900/60 px-4 py-3.5">
              <div className="text-[11px] font-medium uppercase tracking-wide text-gray-500">Overall Δ</div>
              <div
                className={`mt-1 text-2xl font-semibold ${ab.overall_delta >= 0 ? "text-emerald-400" : "text-rose-400"}`}
              >
                {(ab.overall_delta >= 0 ? "+" : "") + (ab.overall_delta * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-500">treatment vs control</div>
            </div>
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3.5">
              <div className="text-[11px] font-medium uppercase tracking-wide text-emerald-400">
                Control wins
              </div>
              <div className="mt-1 text-2xl font-semibold text-emerald-300">{ab.regressed}</div>
              <div className="text-xs text-gray-500">cases control beats treatment</div>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900/60 px-4 py-3.5">
              <div className="text-[11px] font-medium uppercase tracking-wide text-gray-500">
                Treatment wins
              </div>
              <div className="mt-1 text-2xl font-semibold text-gray-50">{ab.improved}</div>
              <div className="text-xs text-gray-500">cases treatment is better</div>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900/60 px-4 py-3.5">
              <div className="text-[11px] font-medium uppercase tracking-wide text-gray-500">Model</div>
              <div className="mt-1 text-sm font-semibold text-gray-50">deterministic</div>
              <div className="text-xs text-gray-500">offline, reproducible</div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Card
              title="Head to head"
              subtitle={`${ab.control} ← vs → ${ab.treatment}`}
            >
              {ab.deltas.length === 0 && <EmptyState title="No dimensions reported" />}
              {ab.deltas.map((d) => (
                <CompareBar
                  key={d.dimension}
                  dimension={d.dimension}
                  a={d.control}
                  b={d.treatment}
                  aLabel="control"
                  bLabel="treatment"
                />
              ))}
            </Card>

            <Card
              title="Per-dimension deltas"
              subtitle="Positive means the treatment improved"
              pad={false}
            >
              <ul className="divide-y divide-gray-800/60">
                {ab.deltas.map((d) => {
                  const pct = d.delta * 100;
                  return (
                    <li key={d.dimension} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                      <span className="w-32 shrink-0 text-xs text-gray-300">{d.dimension}</span>
                      <div className="relative h-1.5 flex-1 overflow-hidden rounded bg-gray-800">
                        <div
                          className="absolute inset-y-0 bg-gray-700"
                          style={{ left: "50%", width: "1px" }}
                        />
                        {Math.abs(pct) > 0.05 && (
                          <div
                            className={
                              pct >= 0
                                ? "absolute inset-y-0 left-1/2 bg-emerald-500/80"
                                : "absolute inset-y-0 right-1/2 bg-rose-500/80"
                            }
                            style={{ width: `${Math.min(50, Math.abs(pct) / 2)}%` }}
                          />
                        )}
                      </div>
                      <span
                        className={`w-16 shrink-0 text-right font-mono text-xs ${
                          pct >= 0 ? "text-emerald-400" : "text-rose-400"
                        }`}
                      >
                        {(pct >= 0 ? "+" : "") + pct.toFixed(1)}%
                      </span>
                    </li>
                  );
                })}
              </ul>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
