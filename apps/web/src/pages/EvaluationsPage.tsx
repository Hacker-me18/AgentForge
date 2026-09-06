import { useState } from "react";
import { api } from "../lib/api";
import type { EvalReport } from "../lib/types";
import { useFetch } from "../lib/useFetch";
import { PageHeader, Card, Stat, Button, Loading, ErrorState, Spinner } from "../components/ui";
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

  const data = report ?? fetch.data;

  const rerun = async () => {
    setRunning(true);
    try {
      setReport(await api.rerunEvalReport());
    } catch (e) {
      // surface via the notice below
      window.alert(e instanceof Error ? e.message : String(e));
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
            {running ? (
              <>
                <Spinner /> Evaluating…
              </>
            ) : (
              "Re-run evaluation"
            )}
          </Button>
        }
      />

      {loading ? (
        <Loading />
      ) : fetch.error && !data ? (
        <ErrorState message={fetch.error} onRetry={fetch.reload} />
      ) : data ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat label="Cases" value={data.case_count} accent="sky" sub={`spec ${data.spec}`} />
            <Stat label="Overall" value={`${Math.round((data.aggregates.overall ?? 0) * 100)}%`} accent="emerald" />
            <Stat label="Avg latency" value={`${data.raw.avg_latency_ms.toFixed(2)} ms`} accent="violet" />
            <Stat label="Avg cost" value={`$${data.raw.avg_cost.toFixed(6)}`} accent="amber" />
            <Stat label="Avg steps" value={data.raw.avg_steps.toFixed(1)} accent="gray" />
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
                />
              ))}
            </Card>

            <Card
              title="Cases"
              subtitle={`${data.raw.completed}/${data.raw.total} completed`}
              pad={false}
            >
              <ul className="max-h-[420px] divide-y divide-gray-800/60 overflow-y-auto">
                {data.results.slice(0, 200).map((c) => {
                  const id = String(c.case_id ?? "");
                  const ok = Number(c.task_success ?? 0) >= 1;
                  const total = Number(c.overall ?? 0);
                  return (
                    <li key={id} className="flex items-center gap-3 px-4 py-1.5 text-xs">
                      <span className={ok ? "text-emerald-400" : "text-amber-400"}>●</span>
                      <span className="w-24 shrink-0 font-mono text-gray-400">{id}</span>
                      <span className="font-mono text-[10px] text-gray-600">status: {String(c.status)}</span>
                      <span className="ml-auto w-14 text-right font-mono text-gray-400">
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
