import { useState } from "react";
import { RotateCw } from "lucide-react";
import { api } from "../lib/api";
import type { AbReport } from "../lib/types";
import { useFetch } from "../lib/useFetch";
import { PageHeader, Card, Stat, Button, Notice, Loading, ErrorState, EmptyState, cx } from "../components/ui";
import { CompareBar } from "../components/charts";

export default function ExperimentsPage() {
  const fetch = useFetch<AbReport>("/api/eval/report/ab");
  const [data, setData] = useState<AbReport | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ab = data ?? fetch.data;

  const rerun = async () => {
    setRunning(true);
    setError(null);
    try {
      setData(await api.rerunAbReport());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const loading = fetch.loading && !ab;
  const deltaClass =
    ab && ab.overall_delta >= 0 ? "text-olivehi" : "text-rust";

  return (
    <div>
      <PageHeader
        title="Experiments"
        desc="A/B the agent routing strategy offline: the routing agent (v1.0) versus a plain echo baseline (v1.1) across the same research dataset. The harness scores both arms so you can ship the version that actually works."
        actions={
          <Button onClick={() => void rerun()} disabled={running}>
            <RotateCw aria-hidden className={running ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"} />
            {running ? "Running…" : "Re-run experiment"}
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <Notice tone="error">Re-run failed: {error}</Notice>
        </div>
      )}

      {loading ? (
        <Loading />
      ) : fetch.error && !ab ? (
        <ErrorState message={fetch.error} onRetry={fetch.reload} />
      ) : ab ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat label="Cases" value={ab.cases} sub={`per arm · ${ab.dataset} dataset`} />
            <Stat
              label="Overall Δ"
              value={`${(ab.overall_delta >= 0 ? "+" : "") + (ab.overall_delta * 100).toFixed(1)}%`}
              valueClass={deltaClass}
              sub="treatment vs control"
            />
            <Stat label="Control wins" value={ab.regressed} sub="cases control beats treatment" />
            <Stat label="Treatment wins" value={ab.improved} sub="cases treatment is better" />
            <Stat label="Model" value={<span className="text-sm">deterministic</span>} sub="offline, reproducible" />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Card title="Head to head" subtitle={`${ab.control} ← vs → ${ab.treatment}`}>
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
              <ul className="divide-y divide-edge/60">
                {ab.deltas.map((d) => {
                  const pct = d.delta * 100;
                  return (
                    <li key={d.dimension} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                      <span className="w-32 shrink-0 text-xs text-sub">{d.dimension}</span>
                      <div className="relative h-1.5 flex-1 overflow-hidden rounded bg-raised">
                        <div aria-hidden className="absolute inset-y-0 bg-edgehi" style={{ left: "50%", width: "1px" }} />
                        {Math.abs(pct) > 0.05 && (
                          <div
                            aria-hidden
                            className={
                              pct >= 0
                                ? "absolute inset-y-0 left-1/2 bg-olive/80"
                                : "absolute inset-y-0 right-1/2 bg-rust/80"
                            }
                            style={{ width: `${Math.min(50, Math.abs(pct) / 2)}%` }}
                          />
                        )}
                      </div>
                      <span
                        className={cx(
                          "w-16 shrink-0 text-right font-mono text-xs",
                          pct >= 0 ? "text-olivehi" : "text-rust",
                        )}
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
