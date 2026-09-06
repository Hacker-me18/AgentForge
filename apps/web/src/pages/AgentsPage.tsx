import { useState } from "react";
import { Play } from "lucide-react";
import { api } from "../lib/api";
import type { AgentInfo, Run } from "../lib/types";
import { fmtAgo } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import { Drawer } from "../components/Drawer";
import { RunView } from "../components/RunView";
import { PageHeader, Card, Tag, ErrorState, Notice } from "../components/ui";

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
      <PageHeader
        title="Agents"
        desc="The built-in demo catalog. Each agent is a first-class definition — persona, allowed capabilities and one-click tasks — and runs through the same harness, policy and budget the API uses."
      />

      {startError && <div className="mb-4"><Notice tone="error">Could not start run: {startError}</Notice></div>}

      {agents.loading ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="space-y-3 rounded-lg border border-edge bg-panel/70 p-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 animate-pulse rounded-lg bg-raised" />
                <div className="flex-1 space-y-2">
                  <div className="h-3.5 w-40 animate-pulse rounded bg-raised" />
                  <div className="h-2.5 w-52 animate-pulse rounded bg-raised" />
                </div>
              </div>
              <div className="space-y-2 pt-2">
                {Array.from({ length: 3 }, (_, j) => (
                  <div key={j} className="h-2.5 w-full animate-pulse rounded bg-raised" />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : agents.error ? (
        <ErrorState message={agents.error} onRetry={agents.reload} />
      ) : (
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
          {(agents.data ?? []).map((agent) => {
            const busy = starting === agent.agent_id;
            return (
              <Card key={agent.agent_id} className="flex flex-col overflow-hidden" pad={false}>
                <div className="flex flex-1 flex-col p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-raised font-mono text-sm font-semibold text-ink ring-1 ring-inset ring-edge">
                      {agent.name.slice(0, 1)}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h2 className="truncate font-serif text-[16px] font-medium tracking-tight text-ink">
                          {agent.name}
                        </h2>
                        {agent.governed && (
                          <span className="rounded-md border border-brand/40 bg-brand/12 px-2 py-0.5 text-[11px] font-medium text-brandhi">
                            {agent.badge || "governed"}
                          </span>
                        )}
                      </div>
                      <div className="mt-0.5 text-xs text-sub">
                        {agent.category} · {runCounts.get(agent.agent_id) ?? 0} runs ·{" "}
                        <span className="font-mono">{agent.agent_id}</span>
                      </div>
                    </div>
                  </div>

                  <p className="mt-3 text-[13px] leading-relaxed text-fg">{agent.description}</p>

                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {agent.capabilities.map((cap) => (
                      <Tag key={cap} className="text-sub">{cap}</Tag>
                    ))}
                    <Tag className="text-sub normal-case">strategy: {agent.strategy}</Tag>
                  </div>

                  <div className="mt-3 border-t border-edge/70 pt-3">
                    <div className="text-[11px] font-medium text-[#8A7C69]">Try one-click</div>
                    <div className="mt-1.5 space-y-px">
                      {agent.suggested_tasks.map((task) => (
                        <button
                          key={task}
                          onClick={() => void launch(agent, task)}
                          disabled={busy}
                          className="group flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left text-[13px] text-sub transition-colors hover:bg-raised/60 hover:text-fg disabled:opacity-50"
                        >
                          <span className="truncate">{task}</span>
                          {busy ? (
                            <span className="shrink-0 text-[11px] text-faint">starting…</span>
                          ) : (
                            <Play
                              aria-hidden
                              className="h-3.5 w-3.5 shrink-0 text-faint transition-colors group-hover:text-brand"
                              strokeWidth={2.5}
                            />
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
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
