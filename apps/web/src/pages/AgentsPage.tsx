import { useState } from "react";
import { api } from "../lib/api";
import type { AgentInfo, Run } from "../lib/types";
import { fmtAgo } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import { Drawer } from "../components/Drawer";
import { RunView } from "../components/RunView";
import { Button, Card, Loading, ErrorState, cx } from "../components/ui";

const CAT_ACCENT: Record<string, string> = {
  Research: "from-sky-500/20 to-sky-500/0 text-sky-300 border-sky-500/30",
  Analytics: "from-violet-500/20 to-violet-500/0 text-violet-300 border-violet-500/30",
  "Governance demo": "from-amber-500/20 to-amber-500/0 text-amber-300 border-amber-500/30",
  General: "from-gray-500/20 to-gray-500/0 text-gray-300 border-gray-500/30",
};

function accent(cat: string) {
  return CAT_ACCENT[cat] ?? CAT_ACCENT.General;
}

export default function AgentsPage() {
  const agents = useFetch<AgentInfo[]>("/api/agents");
  const runs = useFetch<Run[]>("/api/runs?limit=500");
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [starting, setStarting] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  const runCounts = new Map<string, number>();
  for (const r of runs.data ?? []) {
    runCounts.set(r.agent_id, (runCounts.get(r.agent_id) ?? 0) + 1);
  }

  const launch = async (agent: AgentInfo, task: string) => {
    setStarting(agent.agent_id);
    setStartError(null);
    try {
      const record = await api.startRun(task, agent.agent_id);
      setActiveRun(record);
    } catch (e) {
      setStartError(e instanceof Error ? e.message : String(e));
    } finally {
      setStarting(null);
    }
  };

  const agentName = (id: string) => agents.data?.find((a) => a.agent_id === id)?.name ?? id;
  const activeAgent = activeRun ? agentName(activeRun.agent_id) : "";

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-gray-50">Agents</h1>
        <p className="mt-1 max-w-2xl text-sm text-gray-400">
          The built-in demo catalog. Each agent is a first-class definition — persona, allowed
          capabilities and one-click tasks — and runs through the same harness, policy and budget
          the API uses. Click a task to watch a live run.
        </p>
      </div>

      {startError && (
        <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/5 px-4 py-2.5 text-sm text-rose-300">
          Could not start run: {startError}
        </div>
      )}

      {agents.loading ? (
        <Loading />
      ) : agents.error ? (
        <ErrorState message={agents.error} onRetry={agents.reload} />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {(agents.data ?? []).map((agent) => (
            <Card key={agent.agent_id} className="flex flex-col overflow-hidden">
              <div className={cx("border-l-2 border-t-0 border-gray-800 px-4 py-3 bg-gradient-to-br", accent(agent.category))}>
                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-gray-700 bg-gray-900 font-mono text-sm font-bold text-gray-200">
                      {agent.name.slice(0, 1)}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="truncate text-base font-semibold text-gray-50">{agent.name}</h3>
                        {agent.governed && (
                          <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300 ring-1 ring-amber-500/30">
                            {agent.badge || "governed"}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-gray-500">
                        {agent.category} · {runCounts.get(agent.agent_id) ?? 0} runs ·{" "}
                        <span className="font-mono">{agent.agent_id}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-gray-300">{agent.description}</p>
              </div>

              <div className="flex flex-1 flex-col px-4 py-3">
                <div className="flex flex-wrap gap-1.5">
                  {agent.capabilities.map((cap) => (
                    <span
                      key={cap}
                      className="rounded-md bg-gray-800/80 px-1.5 py-0.5 font-mono text-[10.5px] text-gray-300"
                    >
                      {cap}
                    </span>
                  ))}
                  <span className="rounded-md bg-gray-800/40 px-1.5 py-0.5 font-mono text-[10.5px] text-gray-500">
                    strategy: {agent.strategy}
                  </span>
                </div>

                <div className="mt-3">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-600">
                    Try one-click
                  </div>
                  <div className="mt-1.5 space-y-1">
                    {agent.suggested_tasks.map((task) => (
                      <button
                        key={task}
                        onClick={() => void launch(agent, task)}
                        disabled={starting === agent.agent_id}
                        className="group flex w-full items-center justify-between gap-3 rounded-md px-2 py-1 text-left text-xs text-gray-400 hover:bg-gray-800/70 hover:text-gray-100"
                      >
                        <span className="truncate">{task}</span>
                        <span className="shrink-0 font-mono text-[10px] text-gray-600 group-hover:text-sky-400">
                          {starting === agent.agent_id ? "starting…" : "run →"}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Drawer
        open={activeRun !== null}
        onClose={() => setActiveRun(null)}
        title={activeRun ? `${activeAgent}` : ""}
        subtitle={
          activeRun ? (
            <>
              run <span className="font-mono">{activeRun.run_id}</span> · started{" "}
              {fmtAgo(activeRun.created_at)}
            </>
          ) : (
            ""
          )
        }
      >
        {activeRun && <RunView key={activeRun.run_id} runId={activeRun.run_id} />}
      </Drawer>
    </div>
  );
}
