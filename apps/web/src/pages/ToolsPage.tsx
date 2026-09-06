import { useMemo, useState } from "react";
import type { ToolInfo } from "../lib/types";
import { useFetch } from "../lib/useFetch";
import { PageHeader, PolicyBadge, Loading, ErrorState, EmptyState } from "../components/ui";

const RISK_TONE: Record<string, string> = {
  low: "text-emerald-400",
  medium: "text-amber-400",
  high: "text-rose-400",
};

export default function ToolsPage() {
  const tools = useFetch<ToolInfo[]>("/api/tools");
  const [query, setQuery] = useState("");
  const [openSchema, setOpenSchema] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let list = tools.data ?? [];
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (t) => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q),
      );
    }
    return list;
  }, [tools.data, query]);

  return (
    <div>
      <PageHeader
        title="Tools"
        desc="The tool registry every run can call. Each tool carries metadata — description, JSON input schema, risk level, timeout and an optional per-call cost — and is gated by the policy engine before execution."
        actions={
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter tools…"
            className="w-56 rounded-lg border border-gray-700 bg-gray-900 px-3 py-1.5 text-sm text-gray-200 placeholder:text-gray-600 focus:border-sky-500 focus:outline-none"
          />
        }
      />

      {tools.loading ? (
        <Loading />
      ) : tools.error ? (
        <ErrorState message={tools.error} onRetry={tools.reload} />
      ) : filtered.length === 0 ? (
        <EmptyState title="No tools match" />
      ) : (
        <div className="space-y-3">
          {filtered.map((tool) => {
            const risk = RISK_TONE[tool.risk_level] ?? "text-gray-400";
            const open = openSchema === tool.name;
            return (
              <div key={tool.name} className="overflow-hidden rounded-xl border border-gray-800 bg-gray-900/60">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-gray-100">{tool.name}</span>
                      <PolicyBadge action={tool.policy} />
                      <span className={`rounded-md bg-gray-800 px-1.5 py-0.5 text-[10px] font-medium ${risk}`}>
                        {tool.risk_level}
                      </span>
                      <span className="rounded-md bg-gray-800/70 px-1.5 py-0.5 font-mono text-[10px] text-gray-400">
                        timeout {tool.timeout}s
                      </span>
                      {tool.cost > 0 && (
                        <span className="rounded-md bg-gray-800/70 px-1.5 py-0.5 font-mono text-[10px] text-amber-300">
                          +${tool.cost.toFixed(6)}
                        </span>
                      )}
                      <span className="rounded-md bg-gray-800/70 px-1.5 py-0.5 text-[10px] text-gray-500">
                        source: {tool.source}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-gray-400">{tool.description}</p>
                  </div>
                  <button
                    onClick={() => setOpenSchema(open ? null : tool.name)}
                    className="shrink-0 rounded-lg border border-gray-700 px-2.5 py-1 text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                  >
                    {open ? "hide schema" : "JSON schema"}
                  </button>
                </div>
                {open && (
                  <pre className="overflow-x-auto border-t border-gray-800 bg-gray-950/70 px-4 py-3">
                    <code className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-gray-400">
                      {JSON.stringify({ input_schema: tool.input_schema }, null, 2)}
                    </code>
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
