import { useState } from "react";
import { RotateCw } from "lucide-react";
import { api } from "../lib/api";
import type { EvalReport } from "../lib/types";
import { useFetch } from "../lib/useFetch";
import { PageHeader, Card, Stat, Button, Notice, Loading, ErrorState } from "../components/ui";
import { CompareBar } from "../components/charts";

const DIMENSIONS: Array<[string, string]> = [
  ["task_success", "Task success"],
  ["tool_selection", "Tool selection"],
  ["evidence", "Evidence quality"],
  ["policy", "Policy compliance"],
  ["latency", "Latency"],
  ["cost", "Cost efficiency"],
  ["steps", "Step efficiency"],
];

function label(key: string) {
  return DIMENSIONS.find(([k]) => k === key)?.[1] ?? key.replace(/_/g, " ");
}

export default function EvaluationsPage() {
  const fetch = useFetch<EvalReport>("/api/eval/report/eval");
  const [report, setReport] = useState<EvalReport | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const data = report ?? fetch.data;

  const rerun = async () => {
    setRunning(true);
    setError(null);
    try {
      setReport(await api.rerunEvalReport());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const loading = fetch.loading && !data;

  return (
    <div>
      <PageHeader
        title="Evaluations"
        desc="Offline scoring of the research agent against a fixed dataset — task success, tool-selection accuracy, evidence, policy compliance, latency, cost and step economy. Re-runs are deterministic and regenerate the on-disk report."
        actions={
          <Button onClick={() => void rerun()} disabled={running}>
            <RotateCw aria-hidden className={running ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"} />
            {running ? "Evaluating…" : "Re-run evaluation"}
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
      ) : fetch.error && !data ? (
        <ErrorState message={fetch.error} onRetry={fetch.reload} />
      ) : data ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat label="Cases" value={data.case_count} sub={`spec ${data.spec}`} />
            <Stat label="Overall" value={`${Math.round((data.aggregates.overall ?? 0) * 100)}%`} />
            <Stat label="Avg latency" value={`${data.raw.avg_latency_ms.toFixed(2)} ms`} />
            <Stat label="Avg cost" value={`$${data.raw.avg_cost.toFixed(6)}`} />
            <Stat label="Avg steps" value={data.raw.avg_steps.toFixed(1)} />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Card title="Dimension scores" subtitle="Each metric normalised to 0–1 (score vs. ideal)">
              {DIMENSIONS.map(([key, display]) => (
                <CompareBar
                  key={key}
                  dimension={display}
                  a={data.aggregates[key] ?? 0}
                  b={1}
                  aLabel="score"
                  bLabel="ideal"
                  aClass="bg-olive"
                />
              ))}
            </Card>

            <Card
              title="Cases"
              subtitle={`${data.raw.completed}/${data.raw.total} completed`}
              pad={false}
            >
              <ul className="max-h-[420px] divide-y divide-edge/60 overflow-y-auto">
                {data.results.slice(0, 200).map((c) => {
                  const id = String(c.case_id ?? "");
                  const ok = Number(c.task_success ?? 0) >= 1;
                  const total = Number(c.overall ?? 0);
                  return (
                    <li key={id} className="flex items-center gap-3 px-4 py-1.5 text-xs">
                      <span aria-hidden className={ok ? "text-olive" : "text-rust"}>●</span>
                      <span className="w-24 shrink-0 font-mono text-sub">{id}</span>
                      <span className="truncate font-mono text-[10px] text-faint">status: {String(c.status)}</span>
                      <span className="ml-auto w-14 shrink-0 text-right font-mono text-sub">
                        {(total * 100).toFixed(0)}%
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
