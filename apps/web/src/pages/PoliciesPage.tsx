import { useState } from "react";
import { api } from "../lib/api";
import type { PolicyAction, PolicyRule, ToolInfo } from "../lib/types";
import { useFetch } from "../lib/useFetch";
import {
  PageHeader,
  PolicyBadge,
  Stat,
  Notice,
  TableSkeleton,
  ErrorState,
  EmptyState,
  cx,
} from "../components/ui";

const ACTION_INFO: Record<PolicyAction, string> = {
  allow: "Runs without interruption.",
  deny: "Blocked before it can execute.",
  require_approval: "Pauses the run and asks a human.",
};

const SELECTED_STYLE: Record<PolicyAction, string> = {
  allow: "bg-olive/20 text-olivehi ring-1 ring-inset ring-olive/50",
  deny: "bg-rust/15 text-rust ring-1 ring-inset ring-rust/45",
  require_approval: "bg-brand/15 text-brandhi ring-1 ring-inset ring-brand/45",
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
    <div className="flex flex-wrap gap-1" role="group" aria-label="Policy action">
      {opts.map((o) => (
        <button
          key={o}
          disabled={disabled}
          onClick={() => onSelect(o)}
          aria-pressed={value === o}
          className={cx(
            "h-6 rounded-md px-2 text-[11px] font-medium transition-colors disabled:opacity-60",
            value === o
              ? SELECTED_STYLE[o]
              : "bg-raised/50 text-sub hover:bg-raised hover:text-fg",
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
  const [notice, setNotice] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const toolName = (name: string) =>
    tools.data?.find((t) => t.name === name)?.description ?? "";
  const toolDescriptions = new Map((tools.data ?? []).map((t) => [t.name, t.description]));

  const save = async (rule: PolicyRule) => {
    setSaving(true);
    setNotice(null);
    try {
      await api.upsertPolicy(rule);
      rules.reload();
      setNotice({
        tone: "success",
        text: `Saved: ${rule.tool} → ${rule.action.replace("_", " ")}`,
      });
    } catch (e) {
      setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) });
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
        <Stat label="Allow" value={summary.allow} valueClass="text-olivehi" />
        <Stat label="Deny" value={summary.deny} valueClass="text-rust" />
        <Stat label="Requires approval" value={summary.review} valueClass="text-brandhi" />
      </div>

      {notice && (
        <div className="mb-4">
          <Notice tone={notice.tone}>{notice.text}</Notice>
        </div>
      )}

      {rules.loading ? (
        <TableSkeleton rows={6} />
      ) : rules.error ? (
        <ErrorState message={rules.error} onRetry={rules.reload} />
      ) : (rules.data ?? []).length === 0 ? (
        <EmptyState title="No rules" />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-edge">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-edge text-[11px] font-medium text-[#8A7C69]">
                <th scope="col" className="px-4 py-2 font-medium">Tool</th>
                <th scope="col" className="px-4 py-2 font-medium">Description</th>
                <th scope="col" className="px-4 py-2 font-medium">Policy</th>
                <th scope="col" className="px-4 py-2 font-medium">Change</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-edge/60 bg-panel/30">
              {(rules.data ?? []).map((rule) => (
                <tr key={rule.tool} className="transition-colors hover:bg-raised/30">
                  <td className="px-4 py-2.5">
                    <div className="font-mono text-xs font-medium text-fg">{rule.tool}</div>
                    {rule.reason && <div className="mt-0.5 text-[11px] text-faint">{rule.reason}</div>}
                  </td>
                  <td className="max-w-sm px-4 py-2.5 text-xs text-sub">
                    {toolDescriptions.get(rule.tool) ?? toolName(rule.tool)}
                  </td>
                  <td className="px-4 py-2.5 align-top">
                    <PolicyBadge action={rule.action} />
                    <div className="mt-1 max-w-[170px] text-[11px] leading-snug text-faint">
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
