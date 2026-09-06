import { useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import type { ToolInfo } from "../lib/types";
import { useFetch } from "../lib/useFetch";
import {
  PageHeader,
  PolicyBadge,
  Tag,
  TableSkeleton,
  ErrorState,
  EmptyState,
  inputCls,
  cx,
} from "../components/ui";

/* Risk is always carried by the visible word; the warm hue is a reinforcing tint. */
const RISK_TONE: Record<string, string> = {
  low: "text-olivehi",
  medium: "text-[#7C5A22]",
  high: "text-rust",
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
            aria-label="Filter tools"
            className={cx(inputCls, "w-56")}
          />
        }
      />

      {tools.loading ? (
        <TableSkeleton rows={6} />
      ) : tools.error ? (
        <ErrorState message={tools.error} onRetry={tools.reload} />
      ) : filtered.length === 0 ? (
        <EmptyState title="No tools match" />
      ) : (
        <div className="space-y-2.5">
          {filtered.map((tool) => {
            const risk = RISK_TONE[tool.risk_level] ?? "text-faint";
            const open = openSchema === tool.name;
            const schemaId = `schema-${tool.name}`;
            return (
              <div key={tool.name} className="overflow-hidden rounded-lg border border-edge bg-panel/70">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
                      <span className="font-mono text-[13px] font-semibold text-ink">{tool.name}</span>
                      <PolicyBadge action={tool.policy} />
                      <Tag className={risk}>{tool.risk_level}</Tag>
                      <Tag className="text-sub">timeout {tool.timeout}s</Tag>
                      {tool.cost > 0 && <Tag className="text-[#8A7C69]">+${tool.cost.toFixed(6)}</Tag>}
                      <Tag className="text-sub">source: {tool.source}</Tag>
                    </div>
                    <p className="mt-1 text-xs text-sub">{tool.description}</p>
                  </div>
                  <button
                    onClick={() => setOpenSchema(open ? null : tool.name)}
                    aria-expanded={open}
                    aria-controls={schemaId}
                    className="inline-flex h-7 shrink-0 items-center gap-1 rounded-md border border-edgehi px-2.5 text-xs text-sub transition-colors hover:bg-raised hover:text-fg"
                  >
                    <ChevronDown aria-hidden className={cx("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
                    {open ? "hide schema" : "JSON schema"}
                  </button>
                </div>
                {open && (
                  <pre
                    id={schemaId}
                    className="overflow-x-auto border-t border-edge/70 bg-canvas/60 px-4 py-3"
                  >
                    <code className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-sub">
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
