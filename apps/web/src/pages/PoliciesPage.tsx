import { useState } from "react";
import { api } from "../lib/api";
import type { PolicyAction, PolicyRule, ToolInfo } from "../lib/types";
import { useFetch } from "../lib/useFetch";
import { PageHeader, PolicyBadge, Loading, ErrorState, EmptyState, cx } from "../components/ui";

const ACTION_INFO: Record<PolicyAction, string> = {
  allow: "Runs without interruption.",
  deny: "Blocked before it can execute.",
  require_approval: "Pauses the run and asks a human.",
};

function SelectAction({
  value,
  onSelect,
  disabled,
}: {
  value: PolicyAction;
  onSelect: (a: PolicyAction) => void;
  disabled?: boolean;
}) {
  const opts: PolicyAction[] = ["allow", "deny", "require_approval"];
  return (
    <div className="flex flex-wrap gap-1">
      {opts.map((o) => (
        <button
          key={o}
          disabled={disabled}
          onClick={() => onSelect(o)}
          className={cx(
            "rounded-md px-2 py-1 text-[11px] font-medium transition-colors disabled:opacity-60",
            value === o
              ? o === "allow"
                ? "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40"
                : o === "deny"
                  ? "bg-rose-500/20 text-rose-300 ring-1 ring-rose-500/40"
                  : "bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/40"
              : "bg-gray-800/60 text-gray-500 hover:text-gray-300",
          )}
        >
          {o.replace("_", " ")}
        </button>
      ))}
    </div>
  );
}

export default function PoliciesPage() {
  const rules = useFetch<PolicyRule[]>("/api/policies");
  const tools = useFetch<ToolInfo[]>("/api/tools");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const toolName = (name: string) =>
    tools.data?.find((t) => t.name === name)?.description ?? "";
  const toolDescriptions = new Map((tools.data ?? []).map((t) => [t.name, t.description]));

  const save = async (rule: PolicyRule) => {
    setSaving(true);
    setNotice(null);
    try {
      await api.upsertPolicy(rule);
      rules.reload();
      setNotice(`Saved: ${rule.tool} → ${rule.action.replace("_", " ")}`);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const summary = {
    allow: (rules.data ?? []).filter((r) => r.action === "allow").length,
    deny: (rules.data ?? []).filter((r) => r.action === "deny").length,
    review: (rules.data ?? []).filter((r) => r.action === "require_approval").length,
  };

  return (
    <div>
      <PageHeader
        title="Policies"
        desc="The governance layer sits between the agent and every tool call. Each rule maps a tool to an action — allow, deny, or require approval — checked synchronously by the gateway before execution."
      />

      <div className="mb-4 grid grid-cols-3 gap-3">
        {[
          ["allow", summary.allow, "text-emerald-400"],
          ["deny", summary.deny, "text-rose-400"],
          ["requires approval", summary.review, "text-amber-400"],
        ].map(([label, count, color]) => (
          <div key={label} className="rounded-xl border border-gray-800 bg-gray-900/60 px-4 py-3">
            <div className="text-[11px] font-medium uppercase tracking-wide text-gray-500">{label}</div>
            <div className={`mt-1 text-2xl font-semibold ${color}`}>{count}</div>
          </div>
        ))}
      </div>

      {notice && (
        <div
          className={cx(
            "mb-4 rounded-lg border px-4 py-2 text-sm",
            notice.startsWith("Saved")
              ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
              : "border-rose-500/30 bg-rose-500/5 text-rose-300",
          )}
        >
          {notice}
        </div>
      )}

      {rules.loading ? (
        <Loading />
      ) : rules.error ? (
        <ErrorState message={rules.error} onRetry={rules.reload} />
      ) : (rules.data ?? []).length === 0 ? (
        <EmptyState title="No rules" />
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-900 text-[11px] uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-4 py-2 font-medium">Tool</th>
                <th className="hidden px-4 py-2 font-medium md:table-cell">Description</th>
                <th className="px-4 py-2 font-medium">Policy</th>
                <th className="px-4 py-2 font-medium">Change</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/70 bg-gray-900/40">
              {(rules.data ?? []).map((rule) => (
                <tr key={rule.tool} className="hover:bg-gray-800/30">
                  <td className="px-4 py-2.5">
                    <div className="font-mono text-xs font-medium text-gray-100">{rule.tool}</div>
                    {rule.reason && <div className="text-[11px] text-gray-600">{rule.reason}</div>}
                  </td>
                  <td className="hidden max-w-sm px-4 py-2.5 text-xs text-gray-500 md:table-cell">
                    {toolDescriptions.get(rule.tool) ?? toolName(rule.tool)}
                  </td>
                  <td className="px-4 py-2.5">
                    <PolicyBadge action={rule.action} />
                    <div className="mt-1 max-w-[160px] text-[11px] leading-snug text-gray-600">
                      {ACTION_INFO[rule.action]}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <SelectAction
                      disabled={saving}
                      value={rule.action}
                      onSelect={(a) =>
                        a !== rule.action &&
                        void save({ tool: rule.tool, action: a, reason: rule.reason })
                      }
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
